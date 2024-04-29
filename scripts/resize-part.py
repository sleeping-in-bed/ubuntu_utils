from __init__ import *
import re
import argparse


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Resize a disk partition')
    parser.add_argument('part', type=str, help="The part name to resize, e.g. /dev/sda1")
    parser.add_argument('new_size', type=str, help="The new.sh size of the partition, e.g. 64GB, 100%%")
    parser.add_argument('-n', '--not-read-only', action='store_false', default=True,
                        help="Just read and not resize the partition to avoid mistakes, default is true")

    parsed_args = parser.parse_args()
    return parsed_args


if __name__ == '__main__':
    args = get_args()

    match = re.match(r'(.*?)(\d+)', args.part)
    disk = match.group(1)
    partition = match.group(2)

    p_os_system('df -h')
    p_os_system(f'sudo parted {disk} unit GB print free')
    if not args.not_read_only:
        p_os_system(f'sudo parted {disk} resizepart {partition} {args.new_size}')
        p_os_system(f'sudo parted {disk} unit GB print free')
        p_os_system(f'sudo resize2fs {args.part}')
    p_os_system('df -h')
