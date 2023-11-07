from enum import IntEnum
from pathlib import Path
from typing import NamedTuple

from ...common_api import PluginInfo, PropertyInfo, LoaderInfo
from ...common_api import Buffer, FileBuffer
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       FloatProperty, StringProperty)


def plugin_init():
    pass


def msh_init():
    pass


def msh_load(filepath: str, files: list):
    return {"SUCCESS"}


plugin_info = {
    "name": "HPL2/3 importer",
    "loaders": [
        {
            "name": "Load .msh file",
            "id": "hpl_msh",
            "exts": ("*.msh",),
            "init_fn": msh_init,
            "import_fn": msh_load,
            "properties": []
        }
    ],
    "init_fn": plugin_init
}
