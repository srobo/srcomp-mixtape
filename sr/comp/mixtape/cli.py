from __future__ import division
from __future__ import print_function

from argparse import ArgumentParser
import os.path
import sched
import subprocess
import time
from threading import Thread

from datetime import datetime, timedelta
import dateutil.parser
from dateutil.tz import tzutc
import json
from sseclient import SSEClient
import yaml


current_generation = 0
dev_null = open('/dev/null', 'wb')
exclusivity_groups = {}


def parse_args():
    parser = ArgumentParser(__name__)
    parser.add_argument('stream')
    parser.add_argument('mixtape')
    parser.add_argument('--latency', '-l', type=int, default=950,
                        help='In milliseconds.')
    return parser.parse_args()


def play_track(filename, generation_number, output_device, group):
    global exclusivity_groups

    if generation_number == current_generation:
        print('Playing', filename)
        args = ['sox', filename, '-t', 'coreaudio']
        if output_device is not None:
            args.append(output_device)

        if group is not None:
            existing_process = exclusivity_groups.get(group, None)
            if existing_process is not None:
                existing_process.terminate()

        process = subprocess.Popen(args, stdout=dev_null, stderr=dev_null)
        if group is not None:
            exclusivity_groups[group] = process


def mainloop(args):
    global current_generation

    with open(os.path.join(args.mixtape, 'playlist.yaml')) as file:
        playlist = yaml.load(file)

    stream = SSEClient(args.stream)
    for message in stream:
        if message.event == 'match':
            matches = json.loads(message.data)
            if not matches:
                print('Waiting for a match.')
                continue

            current_generation += 1

            match = matches[0]

            if not all(m['num'] == match['num'] for m in matches):
                raise ValueError("Matches don't have the same number.")

            num = match['num']
            tracks = playlist['tracks'].get(num, []) + playlist.get('all', [])

            game_start = dateutil.parser.parse(match['times']['game']['start']) - timedelta(seconds=args.latency / 1000)

            def current_offset():
                return (datetime.now(tzutc()) - game_start).total_seconds()

            schedule = sched.scheduler(current_offset, time.sleep)
            for track in tracks:
                path = os.path.join(args.mixtape, track['filename'])

                # load into filesystem cache
                with open(path, 'rb') as file:
                    file.read(1)

                if track['start'] < current_offset():
                    continue

                output_device = track.get('output_device', None)
                group = track.get('group', None)

                print('Scheduling', path, 'for', track['start'])
                schedule.enterabs(track['start'], 0, play_track,
                                  argument=(path, current_generation,
                                            output_device, group))

            thread = Thread(target=schedule.run)
            thread.daemon = True
            thread.start()


def main():
    args = parse_args()
    mainloop(args)
