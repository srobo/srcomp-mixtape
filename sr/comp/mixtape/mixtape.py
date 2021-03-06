import functools
import os.path
import subprocess
from typing import Any, Dict, Optional

from .audio import AudioController
from .magicq import MagicqController


class Mixtape:
    def __init__(
        self,
        root: str,
        playlist: Any,
        audio_controller: AudioController,
        magicq_controller: Optional[MagicqController],
    ) -> None:
        self.root = root
        self.playlist = playlist
        self.audio_controller = audio_controller
        self.exclusivity_groups: Dict[object, subprocess.Popen[bytes]] = {}
        self.magicq_controller = magicq_controller

    def play_track(self, filename, output_device, group, trim_start):
        if group is not None:
            existing_process = self.exclusivity_groups.get(group, None)
            if existing_process is not None:
                existing_process.terminate()

        process = self.audio_controller.play(filename, output_device, trim_start)

        if group is not None:
            self.exclusivity_groups[group] = process

    def run_cue(self, magicq_playback, magicq_cue):
        if self.magicq_controller is None:
            raise ValueError(
                "Need a magicq_controller to cue {}".format(magicq_cue),
            )
        self.magicq_controller.jump_to_cue(magicq_playback, magicq_cue, 0)

    def generate_play_actions(self, current_offset, match):
        num = match['num']
        tracks = self.playlist['tracks'].get(num, []) + self.playlist.get('all', [])

        for track in tracks:
            try:
                path = os.path.join(self.root, track['filename'])

            except KeyError:
                magicq_playback = track['magicq_playback']
                magicq_cue = track['magicq_cue']

                name = f'MagicQ({magicq_playback}, {magicq_cue})'
                print('Scheduling', name, 'for', track['start'])

                yield track['start'], 0, functools.partial(
                    self.run_cue,
                    magicq_playback,
                    magicq_cue,
                )

            else:
                print('Scheduling', path, 'for', track['start'])

                trim_start = 0
                if track['start'] < current_offset():
                    trim_start = current_offset() - track['start']

                output_device = track.get('output_device', None)
                group = track.get('group', None)

                yield track['start'], 0, functools.partial(
                    self.play_track,
                    path,
                    output_device,
                    group,
                    trim_start,
                )

                # load into filesystem cache
                with open(path, 'rb') as file:
                    file.read(1)
