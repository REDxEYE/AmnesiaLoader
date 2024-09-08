from pathlib import Path
from typing import Iterable


def pop_path_back(path: Path):
    if len(path.parts) > 1:
        return Path().joinpath(*path.parts[1:])
    else:
        return path


_FILE_CACHE = {}


def build_cache(game_root: Path, file_masks: Iterable[str]):
    print("Building cache")
    for mask in file_masks:
        for file in game_root.rglob(mask):
            _FILE_CACHE[file.name.lower()] = file
            _FILE_CACHE[str(file.relative_to(game_root)).lower()] = file
    print(f"Indexed {len(_FILE_CACHE) // 2} files")


def find_file_v2(game_root: Path, file_path: Path):
    # Fast path
    if (game_root / file_path).exists():
        return game_root / file_path
    # Slow path
    second_part = Path(str(file_path).lower())
    for _ in range(len(file_path.parts)):
        if str(second_part) in _FILE_CACHE:
            return _FILE_CACHE[str(second_part)]
        second_part = pop_path_back(second_part)
    # Even slower path
    return glob_backwalk_file_resolver(game_root, file_path)


def glob_backwalk_file_resolver(current_path, file_to_find):
    print(f"resolving path for {file_to_find} in {current_path}")
    current_path = Path(current_path).absolute()
    file_to_find = Path(file_to_find)

    second_part = file_to_find
    for _ in range(len(file_to_find.parts)):
        tmp = next(current_path.rglob("*" + str(second_part)), None)
        if tmp is not None:
            return tmp

        second_part = pop_path_back(second_part)
