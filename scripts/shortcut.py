from __init__ import *
import argparse


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Create a shortcut for a program')
    parser.add_argument('exec', type=str, help="The path of the executable")
    parser.add_argument('-n', '--name', type=str, help="The name of the shortcut")
    parser.add_argument('-i', '--icon', type=str, help="The icon path of the shortcut")

    parsed_args = parser.parse_args()
    return parsed_args


if __name__ == '__main__':
    args = get_args()

    shortcut_path = Path(args.exec)
    args.exec = str(shortcut_path.resolve())
    if not args.name:
        args.name = shortcut_path.stem

    template = f'''[Desktop Entry]
    Name={args.name}
    Exec={args.exec}
    Type=Application
    '''
    if args.icon:
        args.icon = str(Path(args.icon).resolve())
        template += f'Icon={args.icon}'

    shortcut_name = f'{args.name}.desktop'
    desktop_shortcut_path = Path().home() / 'Desktop' / shortcut_name
    desktop_shortcut_path.write_text(template)
    p_os_system(f'chmod +x {str(desktop_shortcut_path)}')
