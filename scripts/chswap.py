from __init__ import *
import argparse


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Change the size of swapfile')
    parser.add_argument('size', type=float, help='The gigabytes number of new.sh swapfile')
    parser.add_argument('-n', '--new', type=str, default='/',
                        help='The new directory where the swapfile is located, default is /')
    parser.add_argument('-o', '--old', type=str, default=None,
                        help='The old directory where the swapfile is located, default equals with the new directory')
    parsed_args = parser.parse_args()
    return parsed_args


if __name__ == '__main__':
    args = get_args()
    new_swapfile_path = Path(args.new) / 'swapfile'
    old_swapfile_path = new_swapfile_path
    if args.old:
        old_swapfile_path = Path(args.old) / 'swapfile'

    execute('sudo swapon --show')
    execute('sudo swapoff -a')
    execute(f'sudo rm {old_swapfile_path}', ignore_error=True)
    execute(f'sudo fallocate -l {args.size}G {new_swapfile_path}', ignore_error=True)
    execute(f'sudo chmod 600 {new_swapfile_path}', ignore_error=True)
    execute(f'sudo mkswap {new_swapfile_path}', ignore_error=True)
    execute(f'sudo swapon {new_swapfile_path}', ignore_error=True)
    execute('sudo swapon --show')
