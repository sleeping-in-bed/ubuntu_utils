from __init__ import *
import argparse


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Change the size of swapfile')
    parser.add_argument('size', type=float, help='The gigabytes number of new.sh swapfile')
    parsed_args = parser.parse_args()
    return parsed_args


if __name__ == '__main__':
    args = get_args()

    p_os_system('sudo swapon --show')
    p_os_system('sudo swapoff -a')
    p_os_system('sudo rm /swapfile')
    p_os_system(f'sudo fallocate -l {args.size}G /swapfile')
    p_os_system('sudo chmod 600 /swapfile')
    p_os_system('sudo mkswap /swapfile')
    p_os_system('sudo swapon /swapfile')
    p_os_system('sudo swapon --show')
