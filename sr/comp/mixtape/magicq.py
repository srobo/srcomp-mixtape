from typing import Union

from pythonosc.udp_client import SimpleUDPClient  # type: ignore[import]


class MagicqController:

    def __init__(self, host: str, port: int) -> None:
        self.osc_client = SimpleUDPClient(host, port)

    def activate_playback(self, playback: int) -> None:
        self.osc_client.send_message(f'/pb/{playback}/go', None)

    def release_playback(self, playback: int) -> None:
        self.osc_client.send_message(f'/pb/{playback}/release', None)

    def jump_to_cue(self, playback: int, cue_id: Union[int, float, str]) -> None:
        self.osc_client.send_message(f'/pb/{playback}/{cue_id}', None)
