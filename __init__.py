import math
from pathlib import Path

import bpy
from mathutils import Euler

from .common_utils import build_cache
from ...common_api.collections_api import get_or_create_collection
from .game import Game
from bpy.props import EnumProperty
from .msh_loader import load_msh
from .map_loader import load_hpl2_map, load_hpl3_map


def plugin_init():
    pass


def msh_init():
    pass


def map_init():
    pass


def detect_game_root(path: Path):
    while len(path.parts) > 1:
        if not (path / "maps").exists():
            path = path.parent
            continue
        if not (path / "static_objects").exists():
            path = path.parent
            continue

        return path


def msh_load(operator, filepath: str, files: list[str]):
    game_root = detect_game_root(Path(filepath))
    collection = get_or_create_collection("test", bpy.context.scene.collection)
    base_path = Path(filepath).parent
    for file in files:
        filepath = base_path / file
        load_msh(game_root, filepath, collection, Game(operator.game))
    return {"FINISHED"}


def map_load(operator, filepath: str, files: list[str]):
    game_root = detect_game_root(Path(filepath))
    build_cache(game_root, ("*.dds", "*.msh", "*.mat", "*.tga", "*.ent"))
    base_path = Path(filepath).parent
    root = bpy.data.objects.new("ROOT", None)
    root.matrix_world = Euler((math.radians(90), 0, 0), "XYZ").to_matrix().to_4x4()
    bpy.context.scene.collection.objects.link(root)

    for file in files:
        filepath = base_path / file
        load_hpl2_map(game_root, filepath, root, Game(operator.game))
    return {"FINISHED"}


def hpm_load(operator, filepath: str, files: list[str]):
    game_root = detect_game_root(Path(filepath))
    build_cache(game_root, ("*.dds", "*.msh", "*.mat", "*.tga", "*.ent"))
    base_path = Path(filepath).parent
    root = bpy.data.objects.new("ROOT", None)
    root.matrix_world = Euler((math.radians(90), 0, 0), "XYZ").to_matrix().to_4x4()
    bpy.context.scene.collection.objects.link(root)

    for file in files:
        filepath = base_path / file
        load_hpl3_map(game_root, filepath, root, Game(operator.game))
    return {"FINISHED"}


plugin_info = {
    "name": "HPL2/3 importer",
    "id": "AmnesiaLoader",
    "description": "HPL2/3 addon, adding support to import Amnesia game assets and other game on this engine",
    "version": (0, 1, 0),
    "loaders": [
        {
            "name": "Load .msh file",
            "id": "hpl_msh",
            "exts": ("*.msh",),
            "init_fn": msh_init,
            "import_fn": msh_load,
            "properties": [
                {
                    "name": "Game",
                    "prop_name": "game",
                    "bl_type": EnumProperty,
                    "kwargs": {
                        "items": [(item.value, item.value, "", i) for i, item in enumerate(Game)]
                    }
                }
            ]
        },
        {
            "name": "Load .map file",
            "id": "hpl_map",
            "exts": ("*.map",),
            "init_fn": map_init,
            "import_fn": map_load,
            "properties": [
                {
                    "name": "Game",
                    "prop_name": "game",
                    "bl_type": EnumProperty,
                    "kwargs": {
                        "items": [(item.value, item.value, "", i) for i, item in enumerate(Game)],
                        "default": Game.OTHER_HPL2.value
                    }
                }
            ]
        },
        {
            "name": "Load .hpm file",
            "id": "hpl_hpm",
            "exts": ("*.hpm",),
            "init_fn": map_init,
            "import_fn": hpm_load,
            "properties": [
                {
                    "name": "Game",
                    "prop_name": "game",
                    "bl_type": EnumProperty,
                    "kwargs": {
                        "items": [(item.value, item.value, "", i) for i, item in enumerate(Game)],
                        "default": Game.OTHER_HPL3.value,
                    }
                }
            ]
        }
    ],
    "init_fn": plugin_init
}
