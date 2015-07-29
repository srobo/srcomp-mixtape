from argparse import ArgumentParser


def parse_args():
    parser = ArgumentParser(__name__)
    parser.add_argument('stream')
    parser.add_argument('playlist')
    return parser.parse_args()


def main():
    args = parse_args()
    print(args)
