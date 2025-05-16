from pathlib import Path
import xml.etree.ElementTree as ET

import bpy

from .common_utils import find_file_v2
from .game import Game
from .resource_types.hpl2.mat import Mat
from ...common_api import Texture,create_node, Nodes, connect_nodes, clear_nodes, create_texture_node, \
    connect_nodes_group



def load_texture(game_root: Path, material_path: Path, texture_path: Path):
    if texture_path.stem + ".tga" in bpy.data.images:
        return bpy.data.images[texture_path.stem + ".tga"]
    if texture_path.suffix == "":
        texture_path = texture_path.with_suffix(".dds")

    resolved_real_path = find_file_v2(game_root, texture_path)
    if resolved_real_path is not None:
        print(f"Loading {resolved_real_path}")

        if resolved_real_path.with_suffix(".tga").exists():
            image = bpy.data.images.load(str(resolved_real_path.with_suffix(".tga")))
        else:
            image = bpy.data.images.load(str(resolved_real_path))
            if image.channels == 0:
                bpy.data.images.remove(image)
                texture = Texture.from_dds(resolved_real_path)
                print(f"Found unsupported texture: {resolved_real_path}: {texture.pixel_format.name}")
                texture.write_tga(resolved_real_path.with_suffix(".tga"))
                image = bpy.data.images.load(str(resolved_real_path.with_suffix(".tga")))

        image["channels"] = image.channels
        image.alpha_mode = 'CHANNEL_PACKED'
        return image
    else:
        print(f"Failed to load {texture_path.name} texture")
        return None


def _add_normal(material: bpy.types.Material, image: bpy.types.Image):
    if image is not None:
        image.colorspace_settings.is_data = True
        image.colorspace_settings.name = 'Non-Color'
    normal_node = create_texture_node(material, image, "normal")
    split_rgb = create_node(material, Nodes.ShaderNodeSeparateRGB)
    connect_nodes(material, normal_node.outputs[0], split_rgb.inputs[0])
    combine_rgb = create_node(material, Nodes.ShaderNodeCombineRGB)
    connect_nodes(material, split_rgb.outputs[0], combine_rgb.inputs[0])
    connect_nodes(material, split_rgb.outputs[1], combine_rgb.inputs[1])
    combine_rgb.inputs[2].default_value = 1.0

    normal_convert_node = create_node(material, Nodes.ShaderNodeNormalMap)
    connect_nodes(material, combine_rgb.outputs[0], normal_convert_node.inputs["Color"])
    return normal_convert_node.outputs[0]
    # connect_nodes(material, normal_convert_node.outputs[0], normal_input)


def create_node_group(material, group_name: str):
    node_tree = material.node_tree
    group_node = node_tree.nodes.new('ShaderNodeGroup')
    group_node.node_tree = bpy.data.node_groups[group_name]
    return group_node


def create_rgb_mix_group(material):
    node_tree = material.node_tree

    # Check if node group already exists
    if 'RGBMixGroup' in bpy.data.node_groups:
        # If it exists, create instance in main node tree and assign the RGB mask
        group_node = node_tree.nodes.new('ShaderNodeGroup')
        group_node.node_tree = bpy.data.node_groups['RGBMixGroup']
        return group_node

    # If it does not exist, create a new node group
    group = bpy.data.node_groups.new('RGBMixGroup', 'ShaderNodeTree')
    group.inputs.new('NodeSocketColor', 'Mask')
    group.inputs.new('NodeSocketColor', 'Texture1')
    group.inputs.new('NodeSocketColor', 'Texture2')
    group.inputs.new('NodeSocketColor', 'Texture3')
    group.outputs.new('NodeSocketColor', 'Color')

    # Create nodes within the group
    group_inputs_node = group.nodes.new('NodeGroupInput')
    group_outputs_node = group.nodes.new('NodeGroupOutput')
    separate_rgb = group.nodes.new('ShaderNodeSeparateRGB')
    multiply_node1 = group.nodes.new('ShaderNodeMixRGB')
    multiply_node2 = group.nodes.new('ShaderNodeMixRGB')
    multiply_node3 = group.nodes.new('ShaderNodeMixRGB')
    add_node1 = group.nodes.new('ShaderNodeMixRGB')
    add_node2 = group.nodes.new('ShaderNodeMixRGB')

    # Set multiply nodes to multiply mode
    multiply_node1.blend_type = 'MULTIPLY'
    multiply_node1.inputs[0].default_value = 1.0
    multiply_node2.blend_type = 'MULTIPLY'
    multiply_node2.inputs[0].default_value = 1.0
    multiply_node3.blend_type = 'MULTIPLY'
    multiply_node3.inputs[0].default_value = 1.0

    # Set add nodes to add mode
    add_node1.blend_type = 'ADD'
    add_node1.inputs[0].default_value = 1.0
    add_node2.blend_type = 'ADD'
    add_node2.inputs[0].default_value = 1.0

    # Connect nodes within the group
    group.links.new(group_inputs_node.outputs['Mask'], separate_rgb.inputs[0])
    group.links.new(separate_rgb.outputs[0], multiply_node1.inputs[1])
    group.links.new(group_inputs_node.outputs['Texture1'], multiply_node1.inputs[2])
    group.links.new(separate_rgb.outputs[1], multiply_node2.inputs[1])
    group.links.new(group_inputs_node.outputs['Texture2'], multiply_node2.inputs[2])
    group.links.new(separate_rgb.outputs[2], multiply_node3.inputs[1])
    group.links.new(group_inputs_node.outputs['Texture3'], multiply_node3.inputs[2])
    group.links.new(multiply_node1.outputs[0], add_node1.inputs[1])
    group.links.new(multiply_node2.outputs[0], add_node1.inputs[2])
    group.links.new(add_node1.outputs[0], add_node2.inputs[1])
    group.links.new(multiply_node3.outputs[0], add_node2.inputs[2])
    group.links.new(add_node2.outputs[0], group_outputs_node.inputs[0])

    # Create group instance in the main node tree
    group_node = node_tree.nodes.new('ShaderNodeGroup')
    group_node.node_tree = group

    return group_node


def create_uv_project_group(material):
    node_tree = material.node_tree

    if 'UVProjectGroup' in bpy.data.node_groups:
        # If it exists, create instance in main node tree and assign the RGB mask
        group_node = node_tree.nodes.new('ShaderNodeGroup')
        group_node.node_tree = bpy.data.node_groups['UVProjectGroup']
        return group_node

    group = bpy.data.node_groups.new('UVProjectGroup', 'ShaderNodeTree')
    group.inputs.new('NodeSocketVector', 'Normal')
    group.outputs.new('NodeSocketVector', 'Mask')

    group_inputs_node = group.nodes.new('NodeGroupInput')
    group_outputs_node = group.nodes.new('NodeGroupOutput')

    separate_xyz = group.nodes.new(Nodes.ShaderNodeSeparateXYZ)

    absolute_x_node = group.nodes.new(Nodes.ShaderNodeMath)
    absolute_x_node.operation = 'ABSOLUTE'

    absolute_z_node = group.nodes.new(Nodes.ShaderNodeMath)
    absolute_z_node.operation = 'ABSOLUTE'

    remap_y_pos_node = group.nodes.new(Nodes.ShaderNodeMapRange)

    remap_y_neg_node = group.nodes.new(Nodes.ShaderNodeMapRange)
    remap_y_neg_node.inputs[2].default_value = -1

    add_node = group.nodes.new(Nodes.ShaderNodeMath)
    add_node.operation = 'ADD'

    subtract0_node = group.nodes.new(Nodes.ShaderNodeMath)
    subtract0_node.operation = 'SUBTRACT'
    subtract0_node.use_clamp = True

    subtract1_node = group.nodes.new(Nodes.ShaderNodeMath)
    subtract1_node.operation = 'SUBTRACT'
    subtract1_node.use_clamp = True

    combine_xyz = group.nodes.new(Nodes.ShaderNodeCombineXYZ)

    connect_nodes_group(group, group_inputs_node.outputs[0], separate_xyz.inputs[0])

    connect_nodes_group(group, separate_xyz.outputs[0], absolute_x_node.inputs[0])
    connect_nodes_group(group, separate_xyz.outputs[2], absolute_z_node.inputs[0])
    connect_nodes_group(group, separate_xyz.outputs[1], remap_y_pos_node.inputs[0])
    connect_nodes_group(group, separate_xyz.outputs[1], remap_y_neg_node.inputs[0])

    connect_nodes_group(group, absolute_x_node.outputs[0], add_node.inputs[0])
    connect_nodes_group(group, absolute_z_node.outputs[0], add_node.inputs[1])

    connect_nodes_group(group, add_node.outputs[0], subtract0_node.inputs[0])
    connect_nodes_group(group, remap_y_pos_node.outputs[0], subtract0_node.inputs[1])

    connect_nodes_group(group, subtract0_node.outputs[0], subtract1_node.inputs[0])
    connect_nodes_group(group, remap_y_neg_node.outputs[0], subtract1_node.inputs[1])

    connect_nodes_group(group, subtract1_node.outputs[0], combine_xyz.inputs[0])
    connect_nodes_group(group, remap_y_pos_node.outputs[0], combine_xyz.inputs[1])
    connect_nodes_group(group, remap_y_neg_node.outputs[0], combine_xyz.inputs[2])

    connect_nodes_group(group, combine_xyz.outputs[0], group_outputs_node.inputs[0])

    group_node = node_tree.nodes.new('ShaderNodeGroup')
    group_node.node_tree = group
    return group_node


def append_blend(filepath, type_name, link=False):
    with bpy.data.libraries.load(filepath, link=link) as (data_from, data_to):
        setattr(data_to, type_name, [asset for asset in getattr(data_from, type_name)])
    for o in getattr(data_to, type_name):
        o.use_fake_user = True


def load_material_nodes():
    if "soliddiffuse" not in bpy.data.node_groups:
        current_path = Path(__file__).parent
        asset_path = current_path / "assets" / "materials.blend"
        append_blend(str(asset_path), "node_groups")


def check_supported_textures(name: str, material_type: str, textures: dict[str, bpy.types.Image],
                             *supported_textures: str):
    textures = textures.copy()
    for supported_texture in supported_textures:
        if supported_texture in textures:
            textures.pop(supported_texture)
    if textures:
        print(f"Material {name}({material_type}) has unhandled textures:")
        for texture in textures.keys():
            print("\t", texture)


def generate_material_nodes(game_root: Path,
                            material_path: Path,
                            material: bpy.types.Material,
                            obj: bpy.types.Object,
                            game: Game):
    load_material_nodes()
    if material.get("LOADED", False):
        return
    material["LOADED"] = True
    material.use_nodes = True

    clear_nodes(material)
    material_path = find_file_v2(game_root, material_path)
    if material_path is None or not material_path.is_file():
        print("Failed to find", material_path)
        return
    with material_path.open("r") as f:
        element = ET.fromstring(f.read())
    xml_material = Mat.from_xml(element).material
    textures = {}
    for texture_type, texture in xml_material.textures.items():
        if texture.file is None:
            continue
        image = load_texture(game_root, material_path.parent, texture.file)
        if image is None:
            continue
        textures[texture_type] = image

    output_node = create_node(material, Nodes.ShaderNodeOutputMaterial)
    material_type = xml_material.main.type.lower()
    blend_mode = xml_material.main.blend_mode.lower()
    params = xml_material.variables

    if game in (Game.DARK_DESCENT, Game.MACHINE_FOR_PIGS, Game.OTHER_HPL2):
        if material_type == "soliddiffuse":
            check_supported_textures(material_path.stem, "soliddiffuse", textures,
                                     "Diffuse",
                                     "NMap",
                                     "Height",
                                     "Alpha",
                                     "Specular",
                                     "Illumination",
                                     )
            shader_node = create_node_group(material, "soliddiffuse")
            alpha_output = None
            if "Diffuse" in textures:
                albedo_node = create_texture_node(material, textures["Diffuse"], "Diffuse")
                connect_nodes(material, albedo_node.outputs[0], shader_node.inputs["Diffuse"])
                if xml_material.main.use_alpha:
                    alpha_output = albedo_node.outputs[1]
            if "NMap" in textures:
                nmap_node = create_texture_node(material, textures["NMap"], "NMap")
                nmap_node.image.colorspace_settings.is_data = True
                nmap_node.image.colorspace_settings.name = 'Non-Color'
                connect_nodes(material, nmap_node.outputs[0], shader_node.inputs["NMap"])
            if "Height" in textures:
                height_node = create_texture_node(material, textures["Height"], "Height")
                height_node.image.colorspace_settings.is_data = True
                height_node.image.colorspace_settings.name = 'Non-Color'
                connect_nodes(material, height_node.outputs[0], shader_node.inputs["Height"])
                shader_node.inputs["HeightMapScale"].default_value = xml_material.main.height_map_scale
                shader_node.inputs["HeightMapBias"].default_value = xml_material.main.height_map_bias
            if "Alpha" in textures:
                alpha_node = create_texture_node(material, textures["Alpha"], "Alpha")
                if textures["Alpha"]["channels"] == 4:
                    alpha_output = alpha_node.outputs[1]
                else:
                    alpha_output = alpha_node.outputs[0]
            if "Specular" in textures:
                specular_node = create_texture_node(material, textures["Specular"], "Specular")
                specular_node.image.colorspace_settings.is_data = True
                specular_node.image.colorspace_settings.name = 'Non-Color'
                connect_nodes(material, specular_node.outputs[0], shader_node.inputs["Specular"])
            else:
                shader_node.inputs["Specular"].default_value = (0, 0, 0, 1)
            if "Illumination" in textures:
                illumination_node = create_texture_node(material, textures["Illumination"], "Illumination")
                connect_nodes(material, illumination_node.outputs[0], shader_node.inputs["Illumination"])

            if alpha_output is not None:
                material.blend_method = 'HASHED'
                material.shadow_method = 'CLIP'
                connect_nodes(material, alpha_output, shader_node.inputs["Alpha"])
            for vv, v in xml_material.variables.items():
                node = create_node(material, Nodes.ShaderNodeValue, vv)
                node.outputs[0].default_value = v
            shader_output = shader_node.outputs[0]
        elif material_type == "translucent":
            check_supported_textures(material_path.stem, "soliddiffuse", textures,
                                     "Diffuse",
                                     "NMap",
                                     "Height",
                                     "Alpha",
                                     "CubeMapAlpha",
                                     )
            shader_node = create_node_group(material, "translucent")
            alpha_output = None
            if "Diffuse" in textures:
                albedo_node = create_texture_node(material, textures["Diffuse"], "Diffuse")
                connect_nodes(material, albedo_node.outputs[0], shader_node.inputs["Diffuse"])
                if xml_material.main.use_alpha:
                    alpha_output = albedo_node.outputs[1]
            if "NMap" in textures:
                nmap_node = create_texture_node(material, textures["NMap"], "NMap")
                nmap_node.image.colorspace_settings.is_data = True
                nmap_node.image.colorspace_settings.name = 'Non-Color'
                connect_nodes(material, nmap_node.outputs[0], shader_node.inputs["NMap"])
            if "Alpha" in textures:
                alpha_node = create_texture_node(material, textures["Alpha"], "Alpha")
                if textures["Alpha"]["channels"] == 4:
                    alpha_output = alpha_node.outputs[1]
                else:
                    alpha_output = alpha_node.outputs[0]
            if "CubeMapAlpha" in textures:
                alpha_node = create_texture_node(material, textures["CubeMapAlpha"], "CubeMapAlpha")
                alpha_output = alpha_node.outputs[1]
            if alpha_output is not None:
                material.blend_method = 'HASHED'
                material.shadow_method = 'CLIP'
                connect_nodes(material, alpha_output, shader_node.inputs["Alpha"])
            shader_node.inputs["Refraction"].default_value = xml_material.variables.get("Refraction", 0)
            shader_output = shader_node.outputs[0]
        elif material_type == "decal":
            check_supported_textures(material_path.stem, "soliddiffuse", textures,
                                     "Diffuse",
                                     "Alpha",
                                     )
            if blend_mode == "add" or blend_mode == "alpha":
                shader_node = create_node_group(material, "decal")
                alpha_output = None
                if "Diffuse" in textures:
                    albedo_node = create_texture_node(material, textures["Diffuse"], "Diffuse")
                    connect_nodes(material, albedo_node.outputs[0], shader_node.inputs["Diffuse"])
                    alpha_output = albedo_node.outputs[1]
                if alpha_output is not None:
                    material.blend_method = 'BLEND'
                    material.shadow_method = 'CLIP'
                    connect_nodes(material, alpha_output, shader_node.inputs["Alpha"])
            elif blend_mode == "mul":
                shader_node = create_node(material, Nodes.ShaderNodeBsdfTransparent, "decal")
                if "Diffuse" in textures:
                    albedo_node = create_texture_node(material, textures["Diffuse"], "Diffuse")
                    connect_nodes(material, albedo_node.outputs[0], shader_node.inputs[0])
                material.blend_method = 'BLEND'
                material.shadow_method = 'CLIP'
            elif blend_mode == "mulx2":
                shader_node = create_node(material, Nodes.ShaderNodeBsdfTransparent, "decal")
                if "Diffuse" in textures:
                    albedo_node = create_texture_node(material, textures["Diffuse"], "Diffuse")
                    connect_nodes(material, albedo_node.outputs[0], shader_node.inputs[0])
                material.blend_method = 'BLEND'
                material.shadow_method = 'CLIP'
            else:
                shader_node = _generate_unsupported_material(material, textures, xml_material)
                print("Unsupported decal blend type", xml_material.main.blend_mode)
            for vv, v in xml_material.variables.items():
                node = create_node(material, Nodes.ShaderNodeValue, vv)
                node.outputs[0].default_value = v
            shader_output = shader_node.outputs[0]
        else:
            print("Unsupported material", xml_material.main.type, material_path)
            shader_node = _generate_unsupported_material(material, textures, xml_material)
            shader_output = shader_node.outputs[0]
    # elif game == Game.BUNKER:
    #     if material_type == "decal":
    #         check_supported_textures(material_path.stem, "decal", textures,
    #                                  "Diffuse",
    #                                  "NMap",
    #                                  "Height",
    #                                  "Specular",
    #                                  )
    #         if blend_mode == "alpha":
    #             shader_node = create_node_group(material, "decal_hpl3")
    #             alpha_output = None
    #             shader_node.inputs["FrenselBias"].default_value = params.get("FrenselBias", 0.2)
    #             shader_node.inputs["FrenselPow"].default_value = params.get("FrenselPow", 8)
    #             if "Diffuse" in textures:
    #                 albedo_node = create_texture_node(material, textures["Diffuse"], "Diffuse")
    #                 connect_nodes(material, albedo_node.outputs[0], shader_node.inputs["Diffuse"])
    #                 alpha_output = albedo_node.outputs[1]
    #             if "NMap" in textures:
    #                 nmap_node = create_texture_node(material, textures["NMap"], "NMap")
    #                 nmap_node.image.colorspace_settings.is_data = True
    #                 nmap_node.image.colorspace_settings.name = 'Non-Color'
    #                 connect_nodes(material, nmap_node.outputs[0], shader_node.inputs["NMap"])
    #             if "Specular" in textures:
    #                 specular_node = create_texture_node(material, textures["Specular"], "Specular")
    #                 connect_nodes(material, specular_node.outputs[0], shader_node.inputs["Specular"])
    #                 connect_nodes(material, specular_node.outputs[1], shader_node.inputs["Roughness"])
    #             if "Height" in textures:
    #                 specular_node = create_texture_node(material, textures["Height"], "Height")
    #                 connect_nodes(material, specular_node.outputs[0], shader_node.inputs["Height"])
    #                 shader_node.inputs["HeightMapScale"].default_value = params.get("HeightMapScale", 0.05)
    #                 shader_node.inputs["HeightMapBias"].default_value = params.get("HeightMapBias", 0)
    #             if alpha_output is not None:
    #                 material.blend_method = 'BLEND'
    #                 material.shadow_method = 'CLIP'
    #                 connect_nodes(material, alpha_output, shader_node.inputs["Alpha"])
    #         elif blend_mode == "mul":
    #             shader_node = create_node(material, Nodes.ShaderNodeBsdfTransparent, "decal")
    #             if "Diffuse" in textures:
    #                 albedo_node = create_texture_node(material, textures["Diffuse"], "Diffuse")
    #                 connect_nodes(material, albedo_node.outputs[0], shader_node.inputs[0])
    #             material.blend_method = 'BLEND'
    #             material.shadow_method = 'CLIP'
    #         else:
    #             shader_node = _generate_unsupported_material(material, textures, xml_material)
    #             print("Unsupported decal blend type", xml_material.main.blend_mode)
    #         shader_output = shader_node.outputs[0]
    #     else:
    #         print("Unsupported material", xml_material.main.type, material_path)
    #         shader_node = _generate_unsupported_material(material, textures, xml_material)
    #         shader_output = shader_node.outputs[0]
    else:
        if material_type == "soliddiffuse":
            specular_node = create_node(material, Nodes.ShaderNodeBsdfGlossy)
            diffuse_node = create_node(material, Nodes.ShaderNodeBsdfDiffuse)
            shader_add = create_node(material, Nodes.ShaderNodeAddShader)
            connect_nodes(material, diffuse_node.outputs[0], shader_add.inputs[0])
            connect_nodes(material, specular_node.outputs[0], shader_add.inputs[1])

            normal_reroute = create_node(material, Nodes.ShaderNodeReroute)
            connect_nodes(material, normal_reroute.outputs[0], specular_node.inputs["Normal"])
            connect_nodes(material, normal_reroute.outputs[0], diffuse_node.inputs["Normal"])

            normal_input = normal_reroute.inputs[0]
            color_input = diffuse_node.inputs[0]
            specular_input = specular_node.inputs[0]
            roughness_input = specular_node.inputs["Roughness"]
            shader_output = shader_add.outputs[0]

            shader_add = create_node(material, Nodes.ShaderNodeAddShader)
            emission_node = create_node(material, Nodes.ShaderNodeEmission)
            connect_nodes(material, shader_output, shader_add.inputs[0])
            connect_nodes(material, emission_node.outputs[0], shader_add.inputs[1])
            emissive_input = emission_node.inputs["Color"]
            emissive_input.default_value = (0, 0, 0, 1)
            shader_output = shader_add.outputs[0]

            shader_mix = create_node(material, Nodes.ShaderNodeMixShader)
            alpha_input = shader_mix.inputs[0]
            alpha_input.default_value = 1.0
            alpha = create_node(material, Nodes.ShaderNodeBsdfTransparent)
            connect_nodes(material, alpha.outputs[0], shader_mix.inputs[1])
            connect_nodes(material, shader_output, shader_mix.inputs[2])
            shader_output = shader_mix.outputs[0]
            material.blend_method = 'BLEND'
            material.blend_method = 'HASHED'

            if "Alpha" in textures:
                specular_node = create_texture_node(material, textures["Alpha"], "Alpha")
                connect_nodes(material, specular_node.outputs[1], alpha_input)
            if "Diffuse" in textures:
                albedo_node = create_texture_node(material, textures["Diffuse"], "Diffuse")
                connect_nodes(material, albedo_node.outputs[0], color_input)
            if "Specular" in textures:
                specular_node = create_texture_node(material, textures["Specular"], "specular")
                invert_node = create_node(material, Nodes.ShaderNodeInvert)
                connect_nodes(material, specular_node.outputs[1], invert_node.inputs[1])
                connect_nodes(material, invert_node.outputs[0], roughness_input)
                connect_nodes(material, specular_node.outputs[0], specular_input)
            if "NMap" in textures:
                connect_nodes(material, _add_normal(material, textures["NMap"]), normal_input)
        elif material_type == "decal":
            diffuse_node = create_node(material, Nodes.ShaderNodeBsdfDiffuse)
            shader_mix = create_node(material, Nodes.ShaderNodeMixShader)
            alpha_input = shader_mix.inputs[0]
            alpha_input.default_value = 1.0
            alpha = create_node(material, Nodes.ShaderNodeBsdfTransparent)
            connect_nodes(material, alpha.outputs[0], shader_mix.inputs[1])
            connect_nodes(material, diffuse_node.outputs[0], shader_mix.inputs[2])
            material.blend_method = 'BLEND'
            material.blend_method = 'BLEND'
            shader_output = shader_mix.outputs[0]

            if "Diffuse" in textures:
                albedo_node = create_texture_node(material, textures["Diffuse"], "Diffuse")
                connect_nodes(material, albedo_node.outputs[0], diffuse_node.inputs[0])
                connect_nodes(material, albedo_node.outputs[1], alpha_input)
        elif material_type == "vertexblend":
            uv_node = create_node(material, Nodes.ShaderNodeUVMap)

            specular_node = create_node(material, Nodes.ShaderNodeBsdfGlossy)
            diffuse_node = create_node(material, Nodes.ShaderNodeBsdfDiffuse)
            shader_add = create_node(material, Nodes.ShaderNodeAddShader)
            connect_nodes(material, diffuse_node.outputs[0], shader_add.inputs[0])
            connect_nodes(material, specular_node.outputs[0], shader_add.inputs[1])

            normal_reroute = create_node(material, Nodes.ShaderNodeReroute)
            connect_nodes(material, normal_reroute.outputs[0], specular_node.inputs["Normal"])
            connect_nodes(material, normal_reroute.outputs[0], diffuse_node.inputs["Normal"])

            normal_input = normal_reroute.inputs[0]
            color_input = diffuse_node.inputs[0]
            specular_input = specular_node.inputs[0]
            roughness_input = specular_node.inputs["Roughness"]
            shader_output = shader_add.outputs[0]

            shader_add = create_node(material, Nodes.ShaderNodeAddShader)
            emission_node = create_node(material, Nodes.ShaderNodeEmission)
            connect_nodes(material, shader_output, shader_add.inputs[0])
            connect_nodes(material, emission_node.outputs[0], shader_add.inputs[1])
            emissive_input = emission_node.inputs["Color"]
            emissive_input.default_value = (0, 0, 0, 1)
            shader_output = shader_add.outputs[0]

            shader_mix = create_node(material, Nodes.ShaderNodeMixShader)
            alpha_input = shader_mix.inputs[0]
            alpha_input.default_value = 1.0
            alpha = create_node(material, Nodes.ShaderNodeBsdfTransparent)
            connect_nodes(material, alpha.outputs[0], shader_mix.inputs[1])
            connect_nodes(material, shader_output, shader_mix.inputs[2])
            shader_output = shader_mix.outputs[0]
            material.blend_method = 'BLEND'
            material.blend_method = 'HASHED'

            color_attribute = create_node(material, Nodes.ShaderNodeVertexColor)
            diffuse_rgb_mixer = create_rgb_mix_group(material)
            connect_nodes(material, color_attribute.outputs[0], diffuse_rgb_mixer.inputs[0])
            connect_nodes(material, diffuse_rgb_mixer.outputs[0], color_input)

            specular_rgb_mixer = create_rgb_mix_group(material)
            connect_nodes(material, color_attribute.outputs[0], specular_rgb_mixer.inputs[0])
            connect_nodes(material, specular_rgb_mixer.outputs[0], specular_input)

            roughness_rgb_mixer = create_rgb_mix_group(material)
            connect_nodes(material, color_attribute.outputs[0], roughness_rgb_mixer.inputs[0])
            invert_node = create_node(material, Nodes.ShaderNodeInvert)
            connect_nodes(material, roughness_rgb_mixer.outputs[0], invert_node.inputs[1])
            connect_nodes(material, invert_node.outputs[0], roughness_input)

            normal_rgb_mixer = create_rgb_mix_group(material)
            connect_nodes(material, color_attribute.outputs[0], normal_rgb_mixer.inputs[0])

            split_rgb = create_node(material, Nodes.ShaderNodeSeparateRGB)
            connect_nodes(material, normal_rgb_mixer.outputs[0], split_rgb.inputs[0])
            combine_rgb = create_node(material, Nodes.ShaderNodeCombineRGB)
            connect_nodes(material, split_rgb.outputs[0], combine_rgb.inputs[0])
            connect_nodes(material, split_rgb.outputs[1], combine_rgb.inputs[1])
            combine_rgb.inputs[2].default_value = 1.0
            normal_convert_node = create_node(material, Nodes.ShaderNodeNormalMap)
            connect_nodes(material, combine_rgb.outputs[0], normal_convert_node.inputs["Color"])
            connect_nodes(material, normal_convert_node.outputs[0], normal_input)

            r_scale = create_node(material, Nodes.ShaderNodeVectorMath)
            r_scale.operation = "MULTIPLY"
            connect_nodes(material, uv_node.outputs[0], r_scale.inputs[0])
            tmp = 1 / float(xml_material.variables.get("TextureUVScaleSide", 1))
            r_scale.inputs[1].default_value = (tmp, tmp, tmp)

            g_scale = create_node(material, Nodes.ShaderNodeVectorMath)
            g_scale.operation = "MULTIPLY"
            connect_nodes(material, uv_node.outputs[0], g_scale.inputs[0])
            tmp = 1 / float(xml_material.variables.get("TextureUVScaleTop", 1))
            g_scale.inputs[1].default_value = (tmp, tmp, tmp)

            b_scale = create_node(material, Nodes.ShaderNodeVectorMath)
            b_scale.operation = "MULTIPLY"
            connect_nodes(material, uv_node.outputs[0], b_scale.inputs[0])
            tmp = 1 / float(xml_material.variables.get("TextureUVScaleBottom", 1))
            b_scale.inputs[1].default_value = (tmp, tmp, tmp)

            if "Diffuse_R" in textures:
                diffuse = create_texture_node(material, textures["Diffuse_R"], "Diffuse_R")
                connect_nodes(material, diffuse.outputs[0], diffuse_rgb_mixer.inputs[1])
                connect_nodes(material, r_scale.outputs[0], diffuse.inputs[0])
            if "Diffuse_G" in textures:
                diffuse = create_texture_node(material, textures["Diffuse_G"], "Diffuse_G")
                connect_nodes(material, diffuse.outputs[0], diffuse_rgb_mixer.inputs[2])
                connect_nodes(material, g_scale.outputs[0], diffuse.inputs[0])
            if "Diffuse_B" in textures:
                diffuse = create_texture_node(material, textures["Diffuse_B"], "Diffuse_B")
                connect_nodes(material, diffuse.outputs[0], diffuse_rgb_mixer.inputs[3])
                connect_nodes(material, b_scale.outputs[0], diffuse.inputs[0])

            if "Specular_R" in textures:
                specular = create_texture_node(material, textures["Specular_R"], "Specular_R")
                connect_nodes(material, specular.outputs[0], specular_rgb_mixer.inputs[1])
                connect_nodes(material, specular.outputs[1], roughness_rgb_mixer.inputs[1])
                connect_nodes(material, r_scale.outputs[0], specular.inputs[0])
            if "Specular_G" in textures:
                specular = create_texture_node(material, textures["Specular_G"], "Specular_G")
                connect_nodes(material, specular.outputs[0], specular_rgb_mixer.inputs[2])
                connect_nodes(material, specular.outputs[1], roughness_rgb_mixer.inputs[2])
                connect_nodes(material, g_scale.outputs[0], specular.inputs[0])
            if "Specular_B" in textures:
                specular = create_texture_node(material, textures["Specular_B"], "Specular_B")
                connect_nodes(material, specular.outputs[0], specular_rgb_mixer.inputs[3])
                connect_nodes(material, specular.outputs[1], roughness_rgb_mixer.inputs[3])
                connect_nodes(material, b_scale.outputs[0], specular.inputs[0])

            if "NMap_R" in textures:
                normal = create_texture_node(material, textures["NMap_R"], "NMap_R")
                connect_nodes(material, normal.outputs[0], normal_rgb_mixer.inputs[1])
                connect_nodes(material, r_scale.outputs[0], normal.inputs[0])
            if "NMap_G" in textures:
                normal = create_texture_node(material, textures["NMap_G"], "NMap_G")
                connect_nodes(material, normal.outputs[0], normal_rgb_mixer.inputs[2])
                connect_nodes(material, g_scale.outputs[0], normal.inputs[0])
            if "NMap_B" in textures:
                normal = create_texture_node(material, textures["NMap_B"], "NMap_B")
                connect_nodes(material, normal.outputs[0], normal_rgb_mixer.inputs[3])
                connect_nodes(material, b_scale.outputs[0], normal.inputs[0])
        elif material_type == "translucent":
            glass_node = create_node(material, Nodes.ShaderNodeBsdfGlass)
            shader_output = glass_node.outputs[0]
            shader_mix = create_node(material, Nodes.ShaderNodeMixShader)
            alpha_input = shader_mix.inputs[0]
            alpha_input.default_value = 1.0
            alpha = create_node(material, Nodes.ShaderNodeBsdfTransparent)
            connect_nodes(material, alpha.outputs[0], shader_mix.inputs[1])
            connect_nodes(material, shader_output, shader_mix.inputs[2])
            material.blend_method = 'BLEND'
            material.blend_method = 'BLEND'
            shader_output = shader_mix.outputs[0]

            if "Diffuse" in textures:
                albedo_node = create_texture_node(material, textures["Diffuse"], "Diffuse")
                connect_nodes(material, albedo_node.outputs[0], glass_node.inputs["Color"])
                connect_nodes(material, albedo_node.outputs[1], alpha_input)
            if "NMap" in textures:
                connect_nodes(material, _add_normal(material, textures["NMap"]), glass_node.inputs["Normal"])
        elif material_type == "projecteduv":
            uv_node = create_node(material, Nodes.ShaderNodeUVMap)

            specular_node = create_node(material, Nodes.ShaderNodeBsdfGlossy)
            diffuse_node = create_node(material, Nodes.ShaderNodeBsdfDiffuse)
            shader_add = create_node(material, Nodes.ShaderNodeAddShader)
            connect_nodes(material, diffuse_node.outputs[0], shader_add.inputs[0])
            connect_nodes(material, specular_node.outputs[0], shader_add.inputs[1])

            normal_reroute = create_node(material, Nodes.ShaderNodeReroute)
            connect_nodes(material, normal_reroute.outputs[0], specular_node.inputs["Normal"])
            connect_nodes(material, normal_reroute.outputs[0], diffuse_node.inputs["Normal"])

            normal_input = normal_reroute.inputs[0]
            color_input = diffuse_node.inputs[0]
            specular_input = specular_node.inputs[0]
            roughness_input = specular_node.inputs["Roughness"]
            shader_output = shader_add.outputs[0]

            shader_add = create_node(material, Nodes.ShaderNodeAddShader)
            emission_node = create_node(material, Nodes.ShaderNodeEmission)
            connect_nodes(material, shader_output, shader_add.inputs[0])
            connect_nodes(material, emission_node.outputs[0], shader_add.inputs[1])
            emissive_input = emission_node.inputs["Color"]
            emissive_input.default_value = (0, 0, 0, 1)
            shader_output = shader_add.outputs[0]

            shader_mix = create_node(material, Nodes.ShaderNodeMixShader)
            alpha_input = shader_mix.inputs[0]
            alpha_input.default_value = 1.0
            alpha = create_node(material, Nodes.ShaderNodeBsdfTransparent)
            connect_nodes(material, alpha.outputs[0], shader_mix.inputs[1])
            connect_nodes(material, shader_output, shader_mix.inputs[2])
            shader_output = shader_mix.outputs[0]
            material.blend_method = 'BLEND'
            material.blend_method = 'HASHED'

            project_node = create_uv_project_group(material)
            normal_node = create_node(material, Nodes.ShaderNodeTexCoord)
            normal_node.object = obj
            connect_nodes(material, normal_node.outputs[1], project_node.inputs[0])

            diffuse_rgb_mixer = create_rgb_mix_group(material)
            connect_nodes(material, project_node.outputs[0], diffuse_rgb_mixer.inputs[0])
            connect_nodes(material, diffuse_rgb_mixer.outputs[0], color_input)

            specular_rgb_mixer = create_rgb_mix_group(material)
            connect_nodes(material, project_node.outputs[0], specular_rgb_mixer.inputs[0])
            connect_nodes(material, specular_rgb_mixer.outputs[0], specular_input)

            roughness_rgb_mixer = create_rgb_mix_group(material)
            connect_nodes(material, project_node.outputs[0], roughness_rgb_mixer.inputs[0])
            invert_node = create_node(material, Nodes.ShaderNodeInvert)
            connect_nodes(material, roughness_rgb_mixer.outputs[0], invert_node.inputs[1])
            connect_nodes(material, invert_node.outputs[0], roughness_input)

            normal_rgb_mixer = create_rgb_mix_group(material)
            connect_nodes(material, project_node.outputs[0], normal_rgb_mixer.inputs[0])

            split_rgb = create_node(material, Nodes.ShaderNodeSeparateRGB)
            connect_nodes(material, normal_rgb_mixer.outputs[0], split_rgb.inputs[0])
            combine_rgb = create_node(material, Nodes.ShaderNodeCombineRGB)
            connect_nodes(material, split_rgb.outputs[0], combine_rgb.inputs[0])
            connect_nodes(material, split_rgb.outputs[1], combine_rgb.inputs[1])
            combine_rgb.inputs[2].default_value = 1.0
            normal_convert_node = create_node(material, Nodes.ShaderNodeNormalMap)
            connect_nodes(material, combine_rgb.outputs[0], normal_convert_node.inputs["Color"])
            connect_nodes(material, normal_convert_node.outputs[0], normal_input)

            side_scale = create_node(material, Nodes.ShaderNodeVectorMath)
            side_scale.operation = "MULTIPLY"
            connect_nodes(material, uv_node.outputs[0], side_scale.inputs[0])
            tmp = float(xml_material.variables.get("TextureUVScaleSide", 1))
            side_scale.inputs[1].default_value = (tmp, tmp, tmp)

            top_scale = create_node(material, Nodes.ShaderNodeVectorMath)
            top_scale.operation = "MULTIPLY"
            connect_nodes(material, uv_node.outputs[0], top_scale.inputs[0])
            tmp = float(xml_material.variables.get("TextureUVScaleTop", 1))
            top_scale.inputs[1].default_value = (tmp, tmp, tmp)

            bottom_scale = create_node(material, Nodes.ShaderNodeVectorMath)
            bottom_scale.operation = "MULTIPLY"
            connect_nodes(material, uv_node.outputs[0], bottom_scale.inputs[0])
            tmp = float(xml_material.variables.get("TextureUVScaleBottom", 1))
            bottom_scale.inputs[1].default_value = (tmp, tmp, tmp)

            if "DiffuseSide" in textures:
                diffuse = create_texture_node(material, textures["DiffuseSide"], "DiffuseSide")
                connect_nodes(material, diffuse.outputs[0], diffuse_rgb_mixer.inputs[1])
                connect_nodes(material, side_scale.outputs[0], diffuse.inputs[0])
            if "DiffuseTop" in textures:
                diffuse = create_texture_node(material, textures["DiffuseTop"], "DiffuseTop")
                connect_nodes(material, diffuse.outputs[0], diffuse_rgb_mixer.inputs[2])
                connect_nodes(material, top_scale.outputs[0], diffuse.inputs[0])
            if "DiffuseBottom" in textures:
                diffuse = create_texture_node(material, textures["DiffuseBottom"], "DiffuseBottom")
                connect_nodes(material, diffuse.outputs[0], diffuse_rgb_mixer.inputs[3])
                connect_nodes(material, bottom_scale.outputs[0], diffuse.inputs[0])

            if "SpecularSide" in textures:
                specular = create_texture_node(material, textures["SpecularSide"], "SpecularSide")
                connect_nodes(material, specular.outputs[0], specular_rgb_mixer.inputs[1])
                connect_nodes(material, specular.outputs[1], roughness_rgb_mixer.inputs[1])
                connect_nodes(material, side_scale.outputs[0], specular.inputs[0])
            if "SpecularTop" in textures:
                specular = create_texture_node(material, textures["SpecularTop"], "SpecularTop")
                connect_nodes(material, specular.outputs[0], specular_rgb_mixer.inputs[2])
                connect_nodes(material, specular.outputs[1], roughness_rgb_mixer.inputs[2])
                connect_nodes(material, top_scale.outputs[0], specular.inputs[0])
            if "SpecularBottom" in textures:
                specular = create_texture_node(material, textures["SpecularBottom"], "SpecularBottom")
                connect_nodes(material, specular.outputs[0], specular_rgb_mixer.inputs[3])
                connect_nodes(material, specular.outputs[1], roughness_rgb_mixer.inputs[3])
                connect_nodes(material, bottom_scale.outputs[0], specular.inputs[0])

            if "NMapSide" in textures:
                normal = create_texture_node(material, textures["NMapSide"], "NMapSide")
                connect_nodes(material, normal.outputs[0], normal_rgb_mixer.inputs[1])
                connect_nodes(material, side_scale.outputs[0], normal.inputs[0])
            if "NMapTop" in textures:
                normal = create_texture_node(material, textures["NMapTop"], "NMapTop")
                connect_nodes(material, normal.outputs[0], normal_rgb_mixer.inputs[2])
                connect_nodes(material, top_scale.outputs[0], normal.inputs[0])
            if "NMapBottom" in textures:
                normal = create_texture_node(material, textures["NMapBottom"], "NMapBottom")
                connect_nodes(material, normal.outputs[0], normal_rgb_mixer.inputs[3])
                connect_nodes(material, bottom_scale.outputs[0], normal.inputs[0])
        else:
            print(f"Unsupported material {xml_material.main.type}, {material_path}.")
            return

    connect_nodes(material, output_node.inputs[0], shader_output)


def _generate_unsupported_material(material, textures, xml_material):
    for tt, t in textures.items():
        create_texture_node(material, t, tt)
    for vv, v in xml_material.variables.items():
        if isinstance(v, list):
            node = create_node(material, Nodes.ShaderNodeRGB, vv)
            if len(v) < 4:
                v = v + [0, 0, 0, 0][:4 - len(v)]
        else:
            node = create_node(material, Nodes.ShaderNodeValue, vv)
        if isinstance(v, str):
            continue
        node.outputs[0].default_value = v
    diffuse_node = create_node(material, Nodes.ShaderNodeBsdfDiffuse, xml_material.main.type)
    return diffuse_node
