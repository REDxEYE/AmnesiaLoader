from pathlib import Path
import xml.etree.ElementTree as ET

import bpy
from mathutils import Matrix, Vector, Euler

from AmnesiaLoader.common_loaders import load_entity
from AmnesiaLoader.common_utils import get_or_create_collection
from AmnesiaLoader.resource_types.common import Game
from AmnesiaLoader.resource_types.hpl2.ent import EntityFile as EntityFileHPL2
from AmnesiaLoader.resource_types.hpl3.ent import EntityFile as EntityFileHPL3
from main_msh import load_msh


def _get_all_objects(obj: bpy.types.Object):
    objects = {obj.name: obj}
    for child in obj.children:
        objects.update(_get_all_objects(child))
    return objects


def load_ent(game_root: Path, ent_path: Path, parent_collection: bpy.types.Collection, game: Game):
    root = ET.parse(ent_path).getroot()
    if game in [Game.DARK_DESCENT]:
        entity_data = EntityFileHPL2.from_xml(root)
    elif game in [Game.SOMA, Game.BUNKER]:
        entity_data = EntityFileHPL3.from_xml(root)
    else:
        raise NotImplementedError(f"Entity objects from {game} are not supported")
    file_collection = get_or_create_collection(ent_path.stem, parent_collection)
    mesh_obj, all_objects = load_msh(game_root, entity_data.model_data.mesh.filename.with_suffix(".msh"),
                                     file_collection, game)
    for submesh in entity_data.model_data.mesh.submeshes:
        submesh_obj = bpy.data.objects[all_objects[submesh.name]]
        extra_matrix = Matrix.LocRotScale(Vector(submesh.position), Euler(submesh.rotation), Vector(submesh.scale))
        submesh_obj.matrix_local = submesh_obj.matrix_local @ extra_matrix
        submesh_obj["extra_matrix"] = extra_matrix
    for entity in entity_data.model_data.entities:
        load_entity(entity, mesh_obj, {}, game, file_collection)
    return file_collection.name
