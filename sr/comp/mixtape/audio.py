import logging
import subprocess


class AudioController:

    def __init__(self, audio_backend: str) -> None:
        self.audio_backend = audio_backend

    def play(
        self,
        filename: str,
        output_device: str,
        trim_start: float,
    ) -> 'subprocess.Popen[bytes]':
        logging.info(f'Playing {filename}')
        args = ['sox', filename, '-t', self.audio_backend]
        if output_device is not None:
            args.append(output_device)
        if trim_start != 0:
            args += ['trim', str(trim_start)]

        return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
