import datetime
import json
import sched
import threading
import time
from typing import Callable, cast, Iterable, List, NewType, Optional, Tuple
from typing_extensions import Protocol, TypedDict

import dateutil.parser
import requests
import sseclient  # type: ignore[import]
from dateutil.tz import tzutc

TLA = NewType('TLA', str)


class Action(Protocol):
    def __call__(self) -> None:
        ...


# (when, priority, callable)
ActionSpec = Tuple[float, int, Action]


class CurrentOffset(Protocol):
    def __call__(self) -> float:
        "Return the current 'time' as will be used during the schedule execution"


class GameTimes(TypedDict):
    end: str
    start: str


class SlotTimes(TypedDict):
    end: str
    start: str


class Times(TypedDict):
    game: GameTimes
    slot: SlotTimes
    staging: object


class Match(TypedDict):
    arena: str
    display_name: str
    num: int
    scores: object
    teams: List[TLA]
    times: Times
    type: object  # noqa:A003


class MatchSchedule(TypedDict):
    matches: List[Match]


def now_utc() -> datetime.datetime:
    return datetime.datetime.now(tzutc())


class Scheduler:
    def __init__(
        self,
        *,
        api_url: str,
        stream_url: str,
        latency: datetime.timedelta,
        generate_actions: Callable[[CurrentOffset, Match], Iterable[ActionSpec]],
    ) -> None:
        self.api_url = api_url
        self.stream = sseclient.SSEClient(stream_url)
        self.latency = latency
        self.generate_actions = generate_actions
        self.current_generation = 0

    def perform_action(self, generation_number: int, action: Callable[[], None]) -> None:
        if generation_number != self.current_generation:
            return

        action()

    def get_match_schedule(self, start_time: datetime.datetime) -> MatchSchedule:
        url = '{}/matches'.format(self.api_url)
        params = {
            'slot_start_time': start_time.isoformat() + '..',
        }
        return cast(MatchSchedule, requests.get(url, params=params).json())

    def create_schedule_from(self, match: Match) -> sched.scheduler:
        num = match['num']
        print("Entering period for match", num)
        game_start = dateutil.parser.parse(match['times']['game']['start']) - self.latency

        def current_offset() -> float:
            """
            The number of seconds since the match began.

            If the match has not yet begun, the value returned is negative.
            """
            return (now_utc() - game_start).total_seconds()

        schedule = sched.scheduler(current_offset, time.sleep)

        for when, priority, action in self.generate_actions(current_offset, match):
            schedule.enterabs(when, priority, self.perform_action, argument=(
                self.current_generation,
                action,
            ))

        return schedule

    def launch_schedule(self, schedule: sched.scheduler) -> threading.Thread:
        thread = threading.Thread(target=schedule.run)
        thread.daemon = True
        thread.start()
        return thread

    def run(self) -> None:
        prev_match: Optional[Match] = None

        for message in self.stream:
            if message.event != 'match':
                continue

            matches = json.loads(message.data)
            if matches:
                match: Match = matches[0]
            else:
                try:
                    match_schedule = self.get_match_schedule(now_utc())
                    match = match_schedule['matches'][0]
                except (KeyError, IndexError):
                    print('Waiting for a match.')
                    continue

            if prev_match is not None:
                if match['num'] == prev_match['num']:
                    if match['times']['game']['start'] == prev_match['times']['game']['start']:
                        continue

            self.current_generation += 1

            schedule = self.create_schedule_from(match)

            self.launch_schedule(schedule)

            prev_match = match
