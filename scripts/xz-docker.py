from __init__ import *
import argparse


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Tar then xz the docker image or unpack')
    parser.add_argument('-i', type=str, help='The image name, compress it using xz')
    parser.add_argument('-d', type=str, help='The archived image path, '
                        'decompress this xz file and load the image to docker')
    parser.add_argument('-r', type=bool, default=False,
                        help='Gets the image from the remote server')
    parser.add_argument('-o', type=str, help='Save path of the archived image')
    parser.add_argument('-c', type=str, default='6', help='Compression level of xz')
    parsed_args = parser.parse_args()
    return parsed_args


if __name__ == '__main__':
    args = get_args()

    if (not args.i and not args.d) or (args.i and args.d):
        raise argparse.ArgumentError(None, 'Option -d or -i must be given one.')
    if args.i:
        if not args.o:
            args.o = f'{args.i}.tar'
            args.o = args.o.replace('/', '_')
        execute(f'docker save -o {args.o} {args.i}')
        execute(f'nice -n 19 sudo xz -T0 --verbose -{args.c} {args.o}')
        xz_name = args.o + '.xz'
        execute(f'sudo chmod 666 {xz_name}')
        execute(f'sudo xz --list {xz_name}')
    elif args.d:
        if args.r:
            save_path = remote.get_file(f'docker/images/{args.d}')
            args.d = str(save_path)
        execute(f'sudo xz -dk --verbose {args.d}')
        tar_path = args.d.rstrip(".xz")
        execute(f'docker load -i {tar_path}')
        execute(f'sudo rm {tar_path}')
