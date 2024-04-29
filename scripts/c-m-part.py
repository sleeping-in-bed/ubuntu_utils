import re
from __init__ import *
import argparse


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Create then permanently mount a partition of a disk')
    parser.add_argument('disk', type=str, help='The disk to be parted and mounted')
    parser.add_argument('dir', type=str, help='The directory to be mounted to')
    parsed_args = parser.parse_args()
    return parsed_args


if __name__ == '__main__':
    args = get_args()
    parted_command = f'sudo parted {args.disk}'
    p_os_system(f'{parted_command} mklabel gpt')
    p_os_system(f'{parted_command} mkpart primary ext4 0% 100%')
    p_os_system(f'{parted_command} print free')
    partition_name = f'{args.disk}p1' if 'nvme' in args.disk else f'{args.disk}1'
    p_os_system(f'sudo mkfs.ext4 {partition_name}')
    p_os_system(f'sudo mkdir {args.dir}')
    p_os_system(f'sudo mount {partition_name} {args.dir}')
    mounted = capture_output('mount')[0]
    media_path = re.search(rf'{partition_name} on (/.*?) .*', mounted).group(1)
    p_os_system(f'sudo chmod 777 {media_path}')
    p_os_system(f'echo "{partition_name} {args.dir} ext4 defaults 0 0" | sudo tee -a /etc/fstab')
    p_os_system('lsblk')
