from __init__ import *
import argparse


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Enable the hibernate function.')
    parsed_args = parser.parse_args()
    return parsed_args


if __name__ == '__main__':
    args = get_args()

    offset = capture("sudo filefrag -v /swapfile |grep \" 0:\"| awk '{print $4}'").stdout
    offset = re.search(r'(\d+)', offset).group(1)
    print(offset)
    fs = capture('df -h /').stdout
    fs = re.search(r'(/.*?/.*?)\s+', fs).group(1)
    print(fs)
    blkid = capture(f'sudo blkid {fs}').stdout
    uuid = re.search(r'UUID="(.*?)"', blkid).group(1)
    print(uuid)
    file = '/etc/default/grub'
    found = 'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash'
    replaced = f'{found} resume=UUID={uuid} resume_offset={offset}'
    execute(f"sudo sed -i 's/{found}/{replaced}/g' {file}")
    execute('sudo update-grub')
