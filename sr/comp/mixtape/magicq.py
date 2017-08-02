import socket
import struct


class MagicqController:

    def __init__(self, address):
        self.address = address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    @staticmethod
    def build_packet(data):
        length = struct.pack('<H', len(data))
        return b'CREP\0\0\0\0' + length + data

    def send_command_once(self, command):
        self.send_command(command, 1)

    def send_command(self, command, retries=5):
        packet = self.build_packet(command.encode('ascii'))
        for retry in range(retries):
            self.socket.sendto(packet, self.address)

    def activate_playback(self, num):
        self.send_command(f'{num}A')

    def release_playback(self, num):
        self.send_command(f'{num}R')

    def jump_to_cue(self, playback, cue_id, cue_id_dec):
        self.send_command(f'{playback},{cue_id},{cue_id_dec}J')
