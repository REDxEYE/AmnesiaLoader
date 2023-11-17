from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector, Matrix

from .common_utils import find_file_v2
from ...common_api import create_material
from .mat_loader import generate_material_nodes
from .resource_types.common import Game
from .resource_types.msh import Msh, Skeleton


def _create_skeleton(model_name: str, skeleton: Skeleton, game: Game):
    arm_data = bpy.data.armatures.new(model_name + "_ARMDATA")
    arm_obj = bpy.data.objects.new(model_name + "_ARM", arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    arm_obj.show_in_front = True
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')

    for root in skeleton.bones:
        bl_bone = arm_data.edit_bones.new(root.name)
        bl_bone.tail = Vector([0, 0, 0.5 * 1]) + bl_bone.head
        matrix = Matrix(root.matrix)
        bl_bone.matrix = matrix
        for bone, parent_name in root.flatten():
            bl_bone = arm_data.edit_bones.new(bone.name)
            bl_bone.tail = Vector([0, 0, 0.5 * 1]) + bl_bone.head
            if parent_name is not None and parent_name != root.name:
                bl_bone.parent = arm_data.edit_bones[parent_name]
            matrix = Matrix(bone.matrix)
            if bl_bone.parent:
                bl_bone.matrix = bl_bone.parent.matrix @ matrix
            else:
                bl_bone.matrix = matrix
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm_obj


def load_msh(game_root: Path, mesh_path: Path, parent_collection: bpy.types.Collection, game: Game):
    if (game_root / mesh_path).exists():
        resolved_mesh_path = game_root / mesh_path
    else:
        resolved_mesh_path = find_file_v2(game_root, mesh_path)
    if resolved_mesh_path is None:
        print(f"Failed to find file {mesh_path} in {game_root}")
    with resolved_mesh_path.open("rb") as f:
        mesh = Msh.from_file(f)
    parent = bpy.data.objects.new(mesh_path.stem, None)
    if mesh.skeleton:
        skeleton = _create_skeleton(mesh_path.stem, mesh.skeleton, game)
        parent_collection.objects.link(skeleton)
        skeleton.parent = parent
    else:
        skeleton = None
    all_objects = {}
    submeshes = []
    for submesh in mesh.submeshes:
        if "_collider" in submesh.name:
            continue
        mesh_data = bpy.data.meshes.new(submesh.name + f"_MESH")
        mesh_obj = bpy.data.objects.new(submesh.name, mesh_data)
        all_objects[submesh.name] = mesh_obj.name
        submeshes.append(mesh_obj.name)

        mesh_data.from_pydata(submesh.position_data, [], submesh.lod_indices(0)[:, ::-1])
        mesh_data.update(calc_edges=True, calc_edges_loose=True)

        material = create_material(submesh.material.stem, mesh_obj)
        if submesh.material.name != "":
            generate_material_nodes(game_root, submesh.material, material, mesh_obj, game)

        vertex_indices = np.zeros((len(mesh_data.loops, )), dtype=np.uint32)
        mesh_data.loops.foreach_get('vertex_index', vertex_indices)

        mesh_data.polygons.foreach_set("use_smooth", np.ones(len(mesh_data.polygons), np.uint32))
        mesh_data.use_auto_smooth = True
        if submesh.normal_data is not None:
            normals = submesh.normal_data.copy()
            mesh_data.normals_split_custom_set_from_vertices(normals)

        for i in range(5):
            if submesh.uv_data(i) is not None:
                uv_layer = mesh_data.uv_layers.new(name=f"UV{i}")
                uv_data = submesh.uv_data(i).copy()

                uv_data[:, 1] = 1 - uv_data[:, 1]

                uv_layer.data.foreach_set('uv', uv_data[vertex_indices].ravel())
        # if submesh.uv1_tangent_data() is not None:
        #     assert "UV1" not in mesh_data.uv_layers
        #     uv_layer = mesh_data.uv_layers.new(name=f"UV1")
        #     uv_data = submesh.uv1_tangent_data()[:, :2].copy()
        #     uv_data[:, 1] = 1 - uv_data[:, 1]
        #
        #     uv_layer.data.foreach_set('uv', uv_data[vertex_indices].ravel())
        #
        #     uv_layer = mesh_data.uv_layers.new(name=f"UV1_2")
        #     uv_data = submesh.uv1_tangent_data()[:, 2:].copy()
        #
        #     uv_data[:, 1] = 1 - uv_data[:, 1]
        #
        #     uv_layer.data.foreach_set('uv', uv_data[vertex_indices].ravel())
        for i in range(2):
            if submesh.color_data(i) is not None:
                vertex_colors = mesh_data.vertex_colors.new(name=f"COL{i}")
                vertex_colors_data = vertex_colors.data
                colors = submesh.color_data(i)[vertex_indices]
                vertex_colors_data.foreach_set("color", colors.ravel())

        if skeleton is not None:
            all_bones = []
            for root in mesh.skeleton.bones:
                all_bones.append((root, None))
                all_bones.extend(root.flatten())
            weight_groups = {bone[0].name: mesh_obj.vertex_groups.new(name=bone[0].name) for bone in all_bones}
            for vertex, bone_index, weight, in submesh.weights:
                if weight > 0:
                    bone_name = all_bones[bone_index][0].name
                    weight_groups[bone_name].add([int(vertex)], weight, 'REPLACE')
            modifier = mesh_obj.modifiers.new(type="ARMATURE", name="Armature")
            modifier.object = skeleton
        mesh_obj.parent = parent
        mesh_obj.matrix_local = Matrix(submesh.matrix)
        parent_collection.objects.link(mesh_obj)

    parent_collection.objects.link(parent)

    if mesh.nodes:
        all_nodes = []
        for node in mesh.nodes:
            all_nodes.append((node, None))
            all_nodes.extend(node.flatten())
        parent_objects = {}
        parent_objects.update(all_objects)
        for node, parent_name in all_nodes:
            if node.name in parent_objects:
                obj = bpy.data.objects[parent_objects[node.name]]
                if parent_name is not None and obj != bpy.data.objects[parent_objects[parent_name]]:
                    obj.parent = bpy.data.objects[parent_objects[parent_name]]
                obj.matrix_local = Matrix(node.matrix)
            else:
                attachment = bpy.data.objects.new(node.name, None)
                all_objects[node.name] = attachment.name
                parent_objects[node.name] = attachment.name
                attachment.matrix_local = Matrix(node.matrix)
                if parent_name is not None:
                    attachment.parent = bpy.data.objects[parent_objects[parent_name]]
                parent_collection.objects.link(attachment)

    else:
        assert mesh.skeleton is not None
        for root in mesh.skeleton.bones:
            if root.name in all_objects:
                obj = bpy.data.objects[all_objects[root.name]]
                # obj.matrix_local = Matrix(bone.matrix)
                obj.parent = skeleton
                obj.parent_type = 'BONE'
                obj.parent_bone = root.name
            for (bone, parent_name) in root.flatten():
                if bone.name in all_objects:
                    obj = bpy.data.objects[all_objects[bone.name]]
                    # obj.matrix_local = Matrix(bone.matrix)
                    obj.parent = skeleton
                    obj.parent_type = 'BONE'
                    obj.parent_bone = bone.name
        # else:
        #     for (bone, parent_name) in geo_bones.flatten():
        #         assert bone.name in submeshes
        #         obj = bpy.data.objects[submeshes[bone.name]]
        #         if parent_name is not None and parent_name != geo_bones.name:
        #             obj.parent = bpy.data.objects[submeshes[parent_name]]
        #         obj.matrix_local = Matrix(bone.matrix)

    return parent, submeshes
