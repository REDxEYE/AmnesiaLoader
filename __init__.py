import math
from pathlib import Path

import bpy
from mathutils import Euler

from .common_utils import get_or_create_collection, build_cache
from .resource_types.common import Game
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       FloatProperty, StringProperty)
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
        if not (path / "models").exists():
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
    loader = load_hpl3_map if Game(operator.game) in (Game.SOMA, Game.BUNKER, Game.OTHER_HPL3) else load_hpl2_map

    root = bpy.data.objects.new("ROOT", None)
    root.matrix_world = Euler((math.radians(90), 0, 0), "XYZ").to_matrix().to_4x4()
    bpy.context.scene.collection.objects.link(root)

    for file in files:
        filepath = base_path / file
        loader(game_root, filepath, root, Game(operator.game))
    return {"FINISHED"}


plugin_info = {
    "name": "HPL2/3 importer",
    "description": "HPL2/3 addon, adding support to import Amnesia game assets and other game on this engine",
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
                        "items": [(item.value, item.value, "", i) for i, item in enumerate(Game)]
                    }
                }
            ]
        }
    ],
    "init_fn": plugin_init
}
