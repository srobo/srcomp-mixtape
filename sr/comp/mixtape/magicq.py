import socket
import struct
from typing import Tuple


class MagicqController:

    def __init__(self, address: Tuple[str, int]) -> None:
        self.address = address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    @staticmethod
    def build_packet(data: bytes) -> bytes:
        length = struct.pack('<H', len(data))
        return b'CREP\0\0\0\0' + length + data

    def send_command_once(self, command: str) -> None:
        self.send_command(command, 1)

    def send_command(self, command: str, retries: int = 5) -> None:
        packet = self.build_packet(command.encode('ascii'))
        for retry in range(retries):
            self.socket.sendto(packet, self.address)

    def activate_playback(self, num: int) -> None:
        self.send_command(f'{num}A')

    def release_playback(self, num: int) -> None:
        self.send_command(f'{num}R')

    def jump_to_cue(self, playback: int, cue_id: int, cue_id_dec: int) -> None:
        self.send_command(f'{playback},{cue_id},{cue_id_dec}J')
