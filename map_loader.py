from pathlib import Path
import xml.etree.ElementTree as ET

from mathutils import Vector, Quaternion, Matrix

from main_msh import load_msh
from .common_loaders import load_entity
from .common_utils import get_or_create_collection, exclude_collection
from .ent_loader import load_ent
from .map_common import generate_plane, load_decal, load_static_objects
from .resource_types.common import Game
from .resource_types.hpl2.map import HPL2Map
from .resource_types.hpl3.map import HPLMapTrackDecal, HPLMapTrackPrimitive, HPLMapTrackEntity, HPLMapTrackStaticObject, \
    HPLMapTrackDetailMeshes

import bpy


def load_hpl2_map(game_root: Path, map_path: Path, parent_object: bpy.types.Object, game: Game):
    root = ET.parse(map_path).getroot()
    level_data = HPL2Map.from_xml(root)
    level = level_data.level
    map_data = level.map_data
    content = map_data.map_contents
    file_list = content.file_index_static_objects.files

    load_static_objects(file_list, game, game_root, parent_object, content.static_objects.objects)

    collection = get_or_create_collection("Primitives", bpy.context.scene.collection)
    for plane in content.primitives.planes:
        obj = generate_plane(game_root, plane, game)
        collection.objects.link(obj)
        obj.parent = parent_object

    collection = get_or_create_collection("Decals", bpy.context.scene.collection)
    decal_material_list = content.file_index_decals.files
    for decal in content.decals.decals:
        if decal.mesh.positions is None:
            continue
        load_decal(collection, decal, decal_material_list, game, game_root, parent_object)

    collections = {}
    file_list = content.file_index_entities.files
    entity_collection_master = get_or_create_collection("EntitiesSource", bpy.context.scene.collection)

    for file in file_list:
        ent_path = game_root / file.path
        if not ent_path.exists():
            print(f"Missing {ent_path} file")
            file_collection = get_or_create_collection(file.path.stem, entity_collection_master)
            obj = bpy.data.objects.new(ent_path.stem, None)
            obj.empty_display_size = 1
            file_collection.objects.link(obj)
            continue
        collections[file.id] = load_ent(game_root, ent_path, entity_collection_master, game)
    exclude_collection(entity_collection_master)

    for entity in content.entities:
        load_entity(entity, parent_object, collections, game)


def load_hpl3_primitive(game_root: Path, primitive_path: Path, parent_object: bpy.types.Object, game: Game):
    root = ET.parse(primitive_path).getroot()
    hpl_decal = HPLMapTrackPrimitive.from_xml(root)
    collection = get_or_create_collection("Primitives", bpy.context.scene.collection)
    for section in hpl_decal.sections:
        for plane in section.objects:
            obj = generate_plane(game_root, plane, game)
            collection.objects.link(obj)
            obj.parent = parent_object


def load_hpl3_decals(game_root: Path, decal_path: Path, parent_object: bpy.types.Object, game: Game):
    print("Loading decals from", decal_path)
    root = ET.parse(decal_path).getroot()
    hpl_decal = HPLMapTrackDecal.from_xml(root)
    collection = get_or_create_collection("Decals", bpy.context.scene.collection)

    for section in hpl_decal.sections:
        for decal in section.objects:
            if decal.mesh.positions is None:
                continue
            decal_obj = load_decal(collection, decal, section.files, game, game_root, parent_object)
            decal_obj["entity_data"]["entity"]["edited_by"] = section.name
            decal_obj["entity_data"]["entity"]["modified"] = str(decal.modification)


def load_hpl3_entities(game_root: Path, entity_path: Path, parent_object: bpy.types.Object, game: Game):
    print("Loading entities from", entity_path)
    root = ET.parse(entity_path).getroot()
    hpl_static_objects = HPLMapTrackEntity.from_xml(root)
    for section in hpl_static_objects.sections:
        collections = {}
        file_list = section.files
        entity_collection_master = get_or_create_collection("EntitiesSource", bpy.context.scene.collection)

        for file in file_list:
            ent_path = game_root / file.path
            if not ent_path.exists():
                print(f"Missing {ent_path} file")
                file_collection = get_or_create_collection(file.path.stem, entity_collection_master)
                obj = bpy.data.objects.new(ent_path.stem, None)
                obj.empty_display_size = 1
                file_collection.objects.link(obj)
                continue
            collections[file.id] = load_ent(game_root, ent_path, entity_collection_master, game)
        exclude_collection(entity_collection_master)

        for entity in section.objects:
            load_entity(entity, parent_object, collections, game)


def load_hpl3_static_objects(game_root: Path, static_objects_path: Path, parent_object: bpy.types.Object, game: Game):
    print("Loading static props from", static_objects_path)
    root = ET.parse(static_objects_path).getroot()
    hpl_static_objects = HPLMapTrackStaticObject.from_xml(root)

    for section in hpl_static_objects.sections:
        objects = load_static_objects(section.files, game, game_root, parent_object, section.objects)
        for obj, s_obj in zip(objects, section.objects):
            obj["entity_data"]["entity"]["edited_by"] = section.name
            obj["entity_data"]["entity"]["created"] = str(s_obj.creation)
            obj["entity_data"]["entity"]["modified"] = str(s_obj.modification)


def load_hpl3_detail_meshes(game_root: Path, detail_mesh_path: Path, parent_object: bpy.types.Object, game: Game):
    print("Loading detail meshes from", detail_mesh_path)
    root = ET.parse(detail_mesh_path).getroot()
    hpl_detail_meshes = HPLMapTrackDetailMeshes.from_xml(root)
    instance_collection = get_or_create_collection("DetailMeshesInstances", bpy.context.scene.collection)
    source_collection = get_or_create_collection("DetailMeshesSource", bpy.context.scene.collection)
    exclude_collection(source_collection)
    for section in hpl_detail_meshes.sections:
        for detail_mesh in section.objects:
            mesh_collection = get_or_create_collection(detail_mesh.file.stem, source_collection)
            load_msh(game_root, game_root / detail_mesh.file.with_suffix(".msh"), mesh_collection, game)
            # mesh_obj.parent = parent_object

            for i, (id_, pos, rot, rad, col, mod) in enumerate(
                zip(detail_mesh.ids, detail_mesh.positions, detail_mesh.rotations, detail_mesh.radii,
                    detail_mesh.colors, detail_mesh.mod_stamps)):
                obj = bpy.data.objects.new(f"{detail_mesh.file.stem}_{i}", None)
                obj.empty_display_size = 1
                obj.instance_type = 'COLLECTION'
                obj.instance_collection = mesh_collection
                obj.matrix_local = Matrix.LocRotScale(Vector(pos),
                                                      Quaternion(rot),
                                                      Vector((rad, rad, rad)))
                obj.parent = parent_object
                instance_collection.objects.link(obj)
                obj["entity_data"] = {}
                obj["entity_data"]["entity"] = {"edited_by": section.name, "modified": str(mod)}


def load_hpl3_map(game_root: Path, map_path: Path, parent_object: bpy.types.Object, game: Game):
    # load_area(game_root, map_path.with_suffix(".hpm_Area"), root, game)
    # load_compound(game_root, map_path.with_suffix(".hpm_Compound"), root, game)
    load_hpl3_decals(game_root, map_path.with_suffix(".hpm_Decal"), parent_object, game)
    load_hpl3_detail_meshes(game_root, map_path.with_suffix(".hpm_DetailMeshes"), parent_object, game)
    load_hpl3_primitive(game_root, map_path.with_suffix(".hpm_Primitive"), parent_object, game)
    load_hpl3_static_objects(game_root, map_path.with_suffix(".hpm_StaticObject"), parent_object, game)
    load_hpl3_entities(game_root, map_path.with_suffix(".hpm_Entity"), parent_object, game)
