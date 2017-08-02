import subprocess


class AudioController:

    def __init__(self):
        self.dev_null = open('/dev/null', 'wb')

    def play(self, filename, output_device, trim_start):
        print('Playing', filename)
        args = ['sox', filename, '-t', 'coreaudio']
        if output_device is not None:
            args.append(output_device)
        if trim_start != 0:
            args += ['trim', str(trim_start)]

        return subprocess.Popen(args, stdout=self.dev_null, stderr=self.dev_null)
