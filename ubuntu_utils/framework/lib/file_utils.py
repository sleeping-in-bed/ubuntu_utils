import os
from collections.abc import Generator
from pathlib import Path


def get_file_paths(
    folder_path: str | Path,
    relative: bool = False,
    generator: bool = False,
    to_str: bool = False,
) -> list[Path] | list[str] | Generator[str | Path, None, None]:
    def _generate_file_paths() -> Generator[str | Path, None, None]:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if relative:
                    file_path = os.path.relpath(os.path.join(root, file), folder_path)
                else:
                    file_path = os.path.abspath(os.path.join(root, file))
                if not to_str:
                    file_path = Path(file_path)
                yield file_path

    if generator:
        return _generate_file_paths()
    else:
        return list(_generate_file_paths())
