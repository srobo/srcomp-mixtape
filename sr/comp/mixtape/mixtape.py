import functools
import logging
import os.path
import subprocess
from typing import Any, Callable, Dict, Iterator, Optional, Tuple

from .audio import AudioController
from .magicq import MagicqController
from .obs_studio import OBSStudioController
from .scheduling import Action, ActionSpec, Match


def preload(filename: str):
    """
    Helper to force a file into the filesystem cache.
    """
    with open(filename, mode='rb') as f:
        f.read(1)


def populate_filename_placeholder(filename: str, match_num: int) -> str:
    return filename.format(match_num=match_num)


class Mixtape:
    def __init__(
        self,
        root: str,
        playlist: Any,
        audio_controller: AudioController,
        magicq_controller: Optional[MagicqController],
        obs_studio_controller: Optional[OBSStudioController],
    ) -> None:
        self.root = os.path.abspath(root)
        self.playlist = playlist
        self.audio_controller = audio_controller
        self.exclusivity_groups: Dict[object, subprocess.Popen[bytes]] = {}
        self.magicq_controller = magicq_controller
        self.obs_studio_controller = obs_studio_controller

    def get_load_video_action(
        self,
        track: Any,
        current_offset: Callable[[], float],
        match_num: int,
    ) -> Tuple[Action, float]:
        filename = populate_filename_placeholder(track['obs_video'], match_num)
        path = os.path.join(self.root, filename)
        if not os.path.exists(path):
            logging.warning(f"File {path} could not be found, skipping")
            raise FileNotFoundError
        preload(path)

        if self.obs_studio_controller is None:
            raise ValueError(f"Need a obs_studio_controller to play {path}")
        controller = self.obs_studio_controller

        def action() -> None:
            logging.info(f"Loading video {path}")
            controller.load_video(path)

        logging.debug(
            f"Scheduling load OBSStudio({path}) for "
            f"{track['start'] - controller.preroll_time}",
        )
        return action, controller.preroll_time

    def get_play_video_action(
        self,
        track: Any,
        current_offset: Callable[[], float],
        match_num: int,
    ) -> Tuple[Action, str]:
        filename = populate_filename_placeholder(track['obs_video'], match_num)
        path = os.path.join(self.root, filename)

        if self.obs_studio_controller is None:
            raise ValueError(f"Need a obs_studio_controller to play {path}")
        controller = self.obs_studio_controller

        name = f'OBSStudio({path})'

        def action() -> None:
            logging.info(f"Running {name}")
            controller.play_video()

        return action, name

    def get_transition_scene_action(
        self,
        track: Any,
        current_offset: Callable[[], float],
    ) -> Tuple[Action, str]:
        scene = track['obs_scene']

        if self.obs_studio_controller is None:
            raise ValueError(f"Need a obs_studio_controller to transistion to {scene}")
        controller = self.obs_studio_controller

        name = f'OBSStudio(scene={scene})'

        def action() -> None:
            logging.info(f"Running {name}")
            controller.transition_scene(scene)

        return action, name

    def play_track(
        self,
        filename: str,
        output_device: str,
        group: Optional[object],
        trim_start: float,
    ) -> None:
        if group is not None:
            existing_process = self.exclusivity_groups.get(group, None)
            if existing_process is not None:
                existing_process.terminate()

        process = self.audio_controller.play(filename, output_device, trim_start)

        if group is not None:
            self.exclusivity_groups[group] = process

    def get_play_track_action(
        self,
        track: Any,
        current_offset: Callable[[], float],
    ) -> Tuple[Action, str]:
        path = os.path.join(self.root, track['filename'])

        trim_start = 0
        if track['start'] < current_offset():
            trim_start = current_offset() - track['start']

        output_device = track.get('output_device', None)
        group = track.get('group', None)

        preload(path)

        action = functools.partial(
            self.play_track,
            path,
            output_device,
            group,
            trim_start,
        )

        return action, path

    def get_run_cue_action(
        self,
        track: Any,
        current_offset: Callable[[], float],
    ) -> Tuple[Action, str]:
        magicq_playback = track['magicq_playback']
        magicq_cue = track['magicq_cue']

        if self.magicq_controller is None:
            raise ValueError(
                "Need a magicq_controller to cue {}".format(magicq_cue),
            )
        controller = self.magicq_controller

        name = f'MagicQ({magicq_playback}, {magicq_cue})'

        def action() -> None:
            logging.info(f"Running {name}")
            controller.jump_to_cue(magicq_playback, magicq_cue)

        return action, name

    def generate_play_actions(
        self,
        current_offset: Callable[[], float],
        match: Match,
    ) -> Iterator[ActionSpec]:
        num = match['num']
        tracks = self.playlist['tracks'].get(num, []) + self.playlist.get('all', [])

        for idx, track in enumerate(tracks):
            if 'filename' in track:
                action, name = self.get_play_track_action(track, current_offset)
            elif 'magicq_playback' in track:
                action, name = self.get_run_cue_action(track, current_offset)
            elif 'obs_video' in track:
                try:
                    load_action, preroll_time = self.get_load_video_action(
                        track,
                        current_offset,
                        num,
                    )
                except FileNotFoundError:
                    continue
                # priority 1 used since timing of load not critical
                # and we don't want to delay other actions
                yield track['start'] - preroll_time, 1, load_action
                action, name = self.get_play_video_action(track, current_offset, num)
            elif 'obs_scene' in track:
                action, name = self.get_transition_scene_action(track, current_offset)
            else:
                raise ValueError(f"Unknown track type at index {idx} start:{track['start']}")

            logging.debug(F"Scheduling {name} for {track['start']}")
            yield track['start'], 0, action
