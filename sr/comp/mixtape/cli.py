from __future__ import division
from __future__ import print_function

from argparse import ArgumentParser
from datetime import datetime, timedelta
import json
import os.path
import sched
import time
from threading import Thread

import dateutil.parser
from dateutil.tz import tzutc
import requests
from sseclient import SSEClient
import yaml

from .audio import AudioController
from .magicq import MagicqController


audio_controller = AudioController()
magicq_controller = None
current_generation = 0
exclusivity_groups = {}


def parse_args():
    parser = ArgumentParser(__name__)

    subparsers = parser.add_subparsers(help='Command to run.')

    play = subparsers.add_parser('play', help='Play the mixtape.')
    play.add_argument('mixtape')
    play.add_argument('api')
    play.add_argument('stream')
    play.add_argument('--latency', '-l', type=int, default=950,
                      help='In milliseconds.')
    play.set_defaults(command='play')

    verify = subparsers.add_parser('verify', help='Verify the mixtape.')
    verify.add_argument('mixtape')
    verify.set_defaults(command='verify')

    test = subparsers.add_parser('test', help='Test the mixtape.')
    test.add_argument('mixtape')
    test.set_defaults(command='test')

    return parser.parse_args()


def get_match_schedule(base_url, start_time):
    url = '{}/matches'.format(base_url)
    params = {
        'slot_start_time': start_time.isoformat() + '..'
    }
    return requests.get(url, params=params).json()


def play_track(filename, magicq_playback, magicq_cue, generation_number, output_device, group, trim_start):
    global exclusivity_groups

    if generation_number != current_generation:
        return

    if magicq_cue is not None:
        magicq_controller.jump_to_cue(magicq_playback, magicq_cue, 0)

    if filename is not None:
        if group is not None:
            existing_process = exclusivity_groups.get(group, None)
            if existing_process is not None:
                existing_process.terminate()

        process = audio_controller.play(filename, output_device, trim_start)

        if group is not None:
            exclusivity_groups[group] = process


def play(args):
    global current_generation, magicq_controller, magicq_playback

    with open(os.path.join(args.mixtape, 'playlist.yaml')) as file:
        playlist = yaml.load(file)

    if 'magicq' in playlist:
        config = playlist['magicq']
        magicq_controller = MagicqController((config['host'], config['port']))
        magicq_playback = config['playback']

    prev_match = None

    stream = SSEClient(args.stream)
    for message in stream:
        if message.event == 'match':
            matches = json.loads(message.data)
            if matches:
                match = matches[0]

            if not matches:
                try:
                    match = get_match_schedule(args.api, datetime.now(tzutc()))['matches'][0]
                except (KeyError, IndexError):
                    print('Waiting for a match.')
                    continue

            if prev_match is not None:
                if match['num'] == prev_match['num']:
                    if match['times']['game']['start'] == prev_match['times']['game']['start']:
                        continue

            current_generation += 1

            num = match['num']
            print("Entering period for match", num)
            tracks = playlist['tracks'].get(num, []) + playlist.get('all', [])

            game_start = dateutil.parser.parse(match['times']['game']['start']) - timedelta(seconds=args.latency / 1000)

            def current_offset():
                return (datetime.now(tzutc()) - game_start).total_seconds()

            schedule = sched.scheduler(current_offset, time.sleep)
            for track in tracks:
                try:
                    magicq_cue = None
                    path = os.path.join(args.mixtape, track['filename'])

                    # load into filesystem cache
                    with open(path, 'rb') as file:
                        file.read(1)
                except KeyError:
                    magicq_cue = track['magicq_cue']
                    magicq_playback = track['magicq_playback']
                    path = None

                trim_start = 0
                if track['start'] < current_offset():
                    trim_start = current_offset() - track['start']

                output_device = track.get('output_device', None)
                group = track.get('group', None)

                name = path or f'MagicQ({magicq_playback}, {magicq_cue})'

                print('Scheduling', name, 'for', track['start'])
                schedule.enterabs(track['start'], 0, play_track,
                                  argument=(path, magicq_playback, magicq_cue, current_generation,
                                            output_device, group, trim_start))

            thread = Thread(target=schedule.run)
            thread.daemon = True
            thread.start()

            prev_match = match


def verify_tracks(mixtape_dir, tracks):
    for track in tracks:
        try:
            filename = track['filename']
        except KeyError:
            continue
        path = os.path.join(mixtape_dir, filename)
        if not os.path.exists(path):
            print(path, "doesn't exist!")


def verify(args):
    with open(os.path.join(args.mixtape, 'playlist.yaml')) as file:
        playlist = yaml.load(file)

    for num, tracks in playlist['tracks'].items():
        verify_tracks(args.mixtape, tracks)

    verify_tracks(args.mixtape, playlist.get('all', []))


def test(args):
    with open(os.path.join(args.mixtape, 'playlist.yaml')) as file:
        playlist = yaml.load(file)

    config = playlist['magicq']
    magicq_controller = MagicqController((config['host'], config['port']))

    magicq_controller.jump_to_cue(4, 2, 0)
    time.sleep(1)
    #magicq_controller.jump_to_cue(3, 2, 0)


def main():
    args = parse_args()
    if args.command == 'play':
        play(args)
    elif args.command == 'verify':
        verify(args)
    elif args.command == 'test':
        test(args)
