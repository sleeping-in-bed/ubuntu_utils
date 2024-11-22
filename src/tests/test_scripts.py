from pathlib import Path


def check_windows_line_break(directory: str | Path):
    dir_path = Path(directory)
    for file_path in dir_path.rglob('*'):
        if file_path.is_file():
            content = file_path.read_bytes()
            if b'\r\n' in content:
                print(f'File {file_path} has "\\r\\n" line break')
                new_content = content.replace(b'\r\n', b'\n')
                file_path.write_bytes(new_content)


if __name__ == '__main__':
    check_windows_line_break(Path(__file__).parent.parent / 'scripts')
