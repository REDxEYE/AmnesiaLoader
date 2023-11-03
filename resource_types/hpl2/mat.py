from pathlib import Path
from typing import Union
from xml.etree.ElementTree import Element

from AmnesiaLoader.resource_types.common import XmlAutoDeserialize, XChild, XAttr, parse_bool, parse_float_list


class Main(XmlAutoDeserialize):
    depth_test: bool = XAttr("DepthTest", deserializer=parse_bool)
    use_alpha: bool = XAttr("UseAlpha", deserializer=parse_bool)
    physics_material: str = XAttr("PhysicsMaterial")
    type: str = XAttr("Type")
    blend_mode: str = XAttr("BlendMode", default="None")
    height_map_bias: float = XAttr("HeightMapBias", default=0.0)
    height_map_scale: float = XAttr("HeightMapScale", default=1.0)


class Texture(XmlAutoDeserialize):
    anim_frame_time: float = XAttr("AnimFrameTime")
    anim_mode: str = XAttr("AnimMode")
    compress: bool = XAttr("Compress", deserializer=parse_bool)
    file: Path = XAttr("File")


def _parse_texture_units(value: Element):
    textures = {}
    for texture_info in value:
        textures[texture_info.tag] = Texture.from_xml(texture_info)
    return textures


def is_float(element: any) -> bool:
    # If you expect None to be passed:
    if element is None:
        return False
    try:
        float(element)
        return True
    except ValueError:
        return False


def _parse_variables(value: Element):
    variables = {}
    if value is None:
        return variables
    for var in value:
        var_value = var.get("Value")
        if var_value in ["false", "true"]:
            var_value = var_value == "true"
        elif var_value == "None":
            var_value = None
        elif is_float(var_value):
            var_value = float(var_value)
        elif var_value.isnumeric():
            var_value = int(var_value)
        elif var_value.replace(" ", "").isnumeric():
            var_value = parse_float_list(var_value)
        variables[var.get("Name")] = var_value
    return variables


class Material(XmlAutoDeserialize):
    main: Main = XChild("Main")
    textures: dict[str, Texture] = XChild("TextureUnits", deserializer=_parse_texture_units)
    variables: dict[str, Union[float, list[float]]] = XChild("SpecificVariables", deserializer=_parse_variables)


class Mat(XmlAutoDeserialize):
    material: Material = XChild("Material")
