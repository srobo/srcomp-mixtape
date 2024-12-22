import logging
import os.path
import time
import warnings
from argparse import ArgumentParser
from datetime import timedelta
from typing import List, Set

from ruamel import yaml

from .audio import AudioController
from .magicq import MagicqController
from .mixtape import Mixtape, populate_filename_placeholder
from .obs_studio import OBSStudioController
from .scheduling import Scheduler

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S',
)

class IncorrectDirectoryArgumentException(Exception):
    pass

def get_parser():
    parser = ArgumentParser(__name__)

    subparsers = parser.add_subparsers(help='Command to run.')

    play = subparsers.add_parser('play', help='Play the mixtape.')
    play.add_argument(
        'mixtape_directory',
        help='The folder containing the playlist.yaml and audio files',
    )
    play.add_argument('api', help='URL of the SRComp HTTP API')
    play.add_argument('stream', help='URL of the SRComp event stream')
    play.add_argument(
        '--latency',
        '-l',
        type=int,
        default=950,
        help='In milliseconds.',
    )
    play.add_argument(
        '--audio-backend',
        default='coreaudio',
        help="Audio backend passed to `sox`",
    )
    play.set_defaults(command='play')

    verify = subparsers.add_parser(
        'verify',
        help='Verify the audio files in the mixtape are found.',
    )
    verify.add_argument(
        'mixtape_directory',
        help='The folder containing the playlist.yaml and audio files',
    )
    verify.add_argument(
        '--matches',
        help="List of matches or match ranges to test placeholders with, for example '1,3-5'.",
        type=parse_ranges,
    )
    verify.set_defaults(command='verify')

    test = subparsers.add_parser(
        'test',
        help=(
            'Test that the MagicQ configuration can control the lighting '
            'by triggering cue 2 of playback 4.'
        ),
    )
    test.add_argument(
        'mixtape_directory',
        help='The folder containing the playlist.yaml and audio files',
    )
    test.set_defaults(command='test')

    return parser


def parse_ranges(ranges: str) -> Set[int]:
    """
    Parse a comma separated list of numbers which may include ranges
    specified as hyphen-separated numbers.
    From https://stackoverflow.com/questions/6405208
    """
    result: List[int] = []
    for part in ranges.split(','):
        if '-' in part:
            a_, b_ = part.split('-')
            a, b = int(a_), int(b_)
            result.extend(range(a, b + 1))
        else:
            a = int(part)
            result.append(a)
    return set(result)


def play(args):
    with open(os.path.join(args.mixtape_directory, 'playlist.yaml')) as file:
        playlist = yaml.safe_load(file)

    magicq_controller = None
    if 'magicq' in playlist:
        config = playlist['magicq']
        if config['port'] == 6553:
            warnings.warn(
                "You are using the default magicq remote protocol port. "
                "Are you sure your OSC receive port is 6553?",
                stacklevel=1,
            )
        magicq_controller = MagicqController(config['host'], config['port'])

    obs_controller = None
    if 'obs_studio' in playlist:
        config = playlist['obs_studio']
        obs_controller = OBSStudioController(
            config['port'],
            config['password'],
            config['source_name'],
            config['scene_name'],
            config['preroll_time'],
        )

    audio_controller = AudioController(args.audio_backend)

    mixtape = Mixtape(
        args.mixtape_directory,
        playlist,
        audio_controller,
        magicq_controller,
        obs_controller,
    )

    scheduler = Scheduler(
        api_url=args.api,
        stream_url=args.stream,
        latency=timedelta(seconds=args.latency / 1000),
        generate_actions=mixtape.generate_play_actions,
    )

    scheduler.run()


def verify_track(mixtape_dir, filename):
    path = os.path.join(mixtape_dir, filename)
    if not os.path.exists(path):
        print(path, "doesn't exist!")


def verify_tracks(mixtape_dir, tracks, matches):
    for track in tracks:
        try:
            filename = track['filename']
        except KeyError:
            try:
                filename = track['obs_video']
                # The trailing brace is omitted so that placeholders with formatting are caught
                if '{match_num' in filename:
                    if matches:
                        for match in matches:
                            match_filename = populate_filename_placeholder(filename, match)
                            verify_track(mixtape_dir, match_filename)
                    else:
                        print(
                            'Video file name contains a match placeholder, '
                            'please use --matches to test this',
                        )
                    continue
            except KeyError:
                continue
        verify_track(mixtape_dir, filename)


def verify(args):
    with open(os.path.join(args.mixtape_directory, 'playlist.yaml')) as file:
        playlist = yaml.safe_load(file)

    for tracks in playlist['tracks'].values():
        verify_tracks(args.mixtape_directory, tracks, args.matches)

    verify_tracks(args.mixtape_directory, playlist.get('all', []), args.matches)


def test(args):
    with open(os.path.join(args.mixtape_directory, 'playlist.yaml')) as file:
        playlist = yaml.safe_load(file)

    config = playlist['magicq']
    magicq_controller = MagicqController(config['host'], config['port'])

    magicq_controller.jump_to_cue(4, 2)
    time.sleep(10)
    # magicq_controller.jump_to_cue(3, 2.5)


def main():
    parser = get_parser()
    args = parser.parse_args()

    if 'command' not in args:
        parser.print_help()
        return

    if os.path.isfile(args.mixtape_directory):
        exit("File entered for the playlist when directory expected!")

    if args.command == 'play':
        play(args)
    elif args.command == 'verify':
        verify(args)
    elif args.command == 'test':
        test(args)
