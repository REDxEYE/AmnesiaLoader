from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector, Matrix, Euler

from .msh_loader import load_msh
from ...common_api import create_material, get_or_create_collection, exclude_collection, is_blender_4_1
from .mat_loader import generate_material_nodes
from .resource_types.common import Game
from .resource_types.hpl_common.map import PlaneCommon, DecalCommon, File, StaticObjectCommon


def generate_plane(game_root: Path, plane: PlaneCommon, game: Game):
    start_corner = Vector(plane.start_corner)
    end_corner = Vector(plane.end_corner)

    corners = [start_corner, Vector([end_corner.x, start_corner.y, start_corner.z]),
               Vector([start_corner.x, end_corner.y, end_corner.z]), end_corner]

    uv_data = [plane.corner1_uv, plane.corner2_uv, plane.corner3_uv, plane.corner4_uv]

    mesh = bpy.data.meshes.new(name=plane.name)
    obj = bpy.data.objects.new(mesh.name, mesh)

    # mesh.from_pydata(corners, [], [[0, 1, 3, 2]])
    mesh.from_pydata(corners, [], [[2, 3, 1, 0]])
    generate_material_nodes(game_root, plane.material, create_material(plane.material.stem, obj), obj, game)

    obj.matrix_local = Matrix.LocRotScale(Vector(plane.position),
                                          Euler(plane.rotation),
                                          Vector(plane.scale))
    uv_data = np.asarray([
        uv_data[0], uv_data[3],
        uv_data[1], uv_data[2]
    ])
    vertex_indices = np.zeros((len(mesh.loops, )), dtype=np.uint32)
    mesh.loops.foreach_get('vertex_index', vertex_indices)

    uv_layer = mesh.uv_layers.new(name=f"UV")

    uv_layer.data.foreach_set('uv', uv_data[vertex_indices].ravel())
    obj["entity_data"] = {}
    obj["entity_data"]["entity"] = plane.as_dict()

    return obj


def load_decal(collection, decal: DecalCommon, decal_material_list: list[File], game, game_root, parent_object):
    model_name = decal.name
    mesh_data = bpy.data.meshes.new(model_name + f"_MESH")
    mesh_obj = bpy.data.objects.new(model_name, mesh_data)
    mesh_data.from_pydata(decal.mesh.positions[:, :3], [], decal.mesh.indices[:, ::-1])
    mesh_data.update(calc_edges=True, calc_edges_loose=True)
    collection.objects.link(mesh_obj)
    mesh_obj.parent = parent_object
    material = create_material(decal_material_list[decal.material_index].path.stem, mesh_obj)
    generate_material_nodes(game_root, decal_material_list[decal.material_index].path, material, mesh_obj, game)
    vertex_indices = np.zeros((len(mesh_data.loops, )), dtype=np.uint32)
    mesh_data.loops.foreach_get('vertex_index', vertex_indices)
    mesh_data.polygons.foreach_set("use_smooth", np.ones(len(mesh_data.polygons), np.uint32))
    if not is_blender_4_1():
        mesh_data.use_auto_smooth = True
    if decal.mesh.normals is not None:
        normals = decal.mesh.normals.copy()
        mesh_data.normals_split_custom_set_from_vertices(normals)
    if decal.mesh.tex_coords is not None:
        uv_layer = mesh_data.uv_layers.new(name=f"UV")
        uv_data = decal.mesh.tex_coords.copy()[:, :2]

        uv_data[:, 1] = 1 - uv_data[:, 1]

        uv_layer.data.foreach_set('uv', uv_data[vertex_indices].ravel())
    mesh_obj["entity_data"] = {}
    mesh_obj["entity_data"]["entity"] = {}
    mesh_obj["entity_data"]["entity"] = decal.as_dict()
    return mesh_obj


def load_static_objects(file_list: list[File], game: Game, game_root: Path, parent_object,
                        static_objects: list[StaticObjectCommon]):
    collections = {}
    collection_master = get_or_create_collection("StaticObjectsSource", bpy.context.scene.collection)
    collection_instances = get_or_create_collection("StaticObjectsInstances", bpy.context.scene.collection)
    for file in file_list:
        file_collection = get_or_create_collection(f"{file.id}_" + file.path.stem, collection_master)
        collections[file.id] = file_collection.name
        mesh_path = game_root / file.path.with_suffix(".msh")
        if not mesh_path.exists():
            print(f"Missing {mesh_path} file")
            obj = bpy.data.objects.new(mesh_path.stem, None)
            obj.empty_display_size = 1
            file_collection.objects.link(obj)
            continue
        load_msh(game_root, mesh_path, file_collection, game)
    exclude_collection(collection_master)
    objects = []
    for entity in static_objects:
        obj = bpy.data.objects.new(entity.name, None)
        obj.empty_display_size = 1
        obj.instance_type = 'COLLECTION'
        obj.instance_collection = bpy.data.collections[collections[entity.file_index]]
        scale = entity.scale
        scale[0] = max(0.01, scale[0])
        scale[1] = max(0.01, scale[1])
        scale[2] = max(0.01, scale[2])
        obj.matrix_local = Matrix.LocRotScale(Vector(entity.position),
                                              Euler(entity.rotation),
                                              Vector(scale))
        obj.parent = parent_object
        collection_instances.objects.link(obj)
        obj["entity_data"] = {}
        obj["entity_data"]["entity"] = entity.as_dict()
        objects.append(obj)
    return objects
