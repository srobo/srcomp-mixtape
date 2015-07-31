from __future__ import division
from __future__ import print_function

from argparse import ArgumentParser
from datetime import datetime, timedelta
import json
import os.path
import sched
import subprocess
import time
from threading import Thread

import dateutil.parser
from dateutil.tz import tzutc
import requests
from sseclient import SSEClient
import yaml


current_generation = 0
dev_null = open('/dev/null', 'wb')
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

    return parser.parse_args()


def get_match_schedule(base_url, start_time):
    params = {
        'slot_start_time': start_time.isoformat() + '..'
    }
    json = requests.get('{}/matches'.format(base_url), params=params).json()
    return json


def play_track(filename, generation_number, output_device, group, trim_start):
    global exclusivity_groups

    if generation_number == current_generation:
        print('Playing', filename)
        args = ['sox', filename, '-t', 'coreaudio']
        if output_device is not None:
            args.append(output_device)
        if trim_start != 0:
            args += ['trim', str(trim_start)]

        if group is not None:
            existing_process = exclusivity_groups.get(group, None)
            if existing_process is not None:
                existing_process.terminate()

        process = subprocess.Popen(args, stdout=dev_null, stderr=dev_null)
        if group is not None:
            exclusivity_groups[group] = process


def play(args):
    global current_generation

    with open(os.path.join(args.mixtape, 'playlist.yaml')) as file:
        playlist = yaml.load(file)

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

                trim_start = 0
                if track['start'] < current_offset():
                    trim_start = current_offset() - track['start']

                output_device = track.get('output_device', None)
                group = track.get('group', None)

                print('Scheduling', path, 'for', track['start'])
                schedule.enterabs(track['start'], 0, play_track,
                                  argument=(path, current_generation,
                                            output_device, group, trim_start))

            thread = Thread(target=schedule.run)
            thread.daemon = True
            thread.start()

            prev_match = match


def verify_tracks(mixtape_dir, tracks):
    for track in tracks:
        path = os.path.join(mixtape_dir, track['filename'])
        if not os.path.exists(path):
            print(path, "doesn't exist!")


def verify(args):
    with open(os.path.join(args.mixtape, 'playlist.yaml')) as file:
        playlist = yaml.load(file)

    for num, tracks in playlist['tracks'].items():
        verify_tracks(args.mixtape, tracks)

    verify_tracks(args.mixtape, playlist.get('all', []))


def main():
    args = parse_args()
    if args.command == 'play':
        play(args)
    elif args.command == 'verify':
        verify(args)
