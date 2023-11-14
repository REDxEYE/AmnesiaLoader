from pathlib import Path
import xml.etree.ElementTree as ET

import bpy
from mathutils import Matrix, Vector, Euler

from .msh_loader import load_msh
from .common_loaders import load_entity
from ...common_api import get_or_create_collection
from .resource_types.common import Game
from .resource_types.hpl2.ent import EntityFile as EntityFileHPL2
from .resource_types.hpl3.ent import EntityFile as EntityFileHPL3


def _get_all_objects(obj: bpy.types.Object):
    objects = {obj.name: obj}
    for child in obj.children:
        objects.update(_get_all_objects(child))
    return objects


def load_ent(game_root: Path, ent_path: Path, parent_collection: bpy.types.Collection, game: Game):
    # print(f"Loading {ent_path}")
    root = ET.parse(ent_path).getroot()
    if game.value in [Game.DARK_DESCENT.value, Game.MACHINE_FOR_PIGS.value, Game.OTHER_HPL2.value]:
        entity_data = EntityFileHPL2.from_xml(root)
    elif game.value in [Game.SOMA.value, Game.BUNKER.value, Game.OTHER_HPL3.value]:
        entity_data = EntityFileHPL3.from_xml(root)
    else:
        raise NotImplementedError(f"Entity objects from {game} are not supported")
    file_collection = get_or_create_collection(ent_path.stem, parent_collection)
    mesh_obj, submeshes = load_msh(game_root, entity_data.model_data.mesh.filename.with_suffix(".msh"),
                                   file_collection, game)
    for i,submesh in enumerate(entity_data.model_data.mesh.submeshes):
        if submesh.sub_mesh_id is None:
            submesh.sub_mesh_id = i
        if submesh.sub_mesh_id >= len(submeshes):
            continue
        submesh_obj = bpy.data.objects[submeshes[submesh.sub_mesh_id]]
        extra_matrix = Matrix.LocRotScale(Vector(submesh.position), Euler(submesh.rotation), Vector(submesh.scale))
        submesh_obj.matrix_local = submesh_obj.matrix_local @ extra_matrix
        submesh_obj["extra_matrix"] = extra_matrix
    for entity in entity_data.model_data.entities:
        load_entity(entity, mesh_obj, {}, game, file_collection)
    return file_collection.name
