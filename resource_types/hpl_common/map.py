from pathlib import Path

import numpy as np

from UniLoader.common_api.xml_parsing import XmlAutoDeserialize, XAttr, parse_bool, parse_float_list, XChild, \
    parse_np_vec4, parse_np_vec3, parse_np_ivec3, parse_user_variables


class ObjectCommon(XmlAutoDeserialize):
    id: int = XAttr("ID")
    position: list[float] = XAttr("WorldPos", deserializer=parse_float_list)
    rotation: list[float] = XAttr("Rotation", deserializer=parse_float_list)
    scale: list[float] = XAttr("Scale", deserializer=parse_float_list)
    active: bool = XAttr("Active", deserializer=parse_bool, default=True)


class PlaneCommon(ObjectCommon):
    align_to_world_coords: bool = XAttr("AlignToWorldCoords", deserializer=parse_bool)
    cast_shadows: bool = XAttr("CastShadows", deserializer=parse_bool)
    collides: bool = XAttr("Collides", deserializer=parse_bool)
    corner1_uv: list[float] = XAttr("Corner1UV", deserializer=parse_float_list)
    corner2_uv: list[float] = XAttr("Corner2UV", deserializer=parse_float_list)
    corner3_uv: list[float] = XAttr("Corner3UV", deserializer=parse_float_list)
    corner4_uv: list[float] = XAttr("Corner4UV", deserializer=parse_float_list)
    start_corner: list[float] = XAttr("StartCorner", deserializer=parse_float_list)
    end_corner: list[float] = XAttr("EndCorner", deserializer=parse_float_list)
    material: Path = XAttr("Material")
    name: str = XAttr("Name")
    texture_angle: float = XAttr("TextureAngle")
    tile_amount: list[float] = XAttr("TileAmount", deserializer=parse_float_list)
    tile_offset: list[float] = XAttr("TileOffset", deserializer=parse_float_list)

    def as_dict(self):
        return {
            "id": self.id,
            "active": self.active,
            "align_to_world_coords": self.align_to_world_coords,
            "cast_shadows": self.cast_shadows,
            "collides": self.collides,
            "texture_angle": self.texture_angle,
            "tile_amount": self.tile_amount,
            "tile_offset": self.tile_offset,
        }


class DecalMesh(XmlAutoDeserialize):
    positions: np.ndarray = XChild("Positions", deserializer=lambda v: parse_np_vec4(v.get("Array")) if v is not None else None)
    normals: np.ndarray = XChild("Normals", deserializer=lambda v: parse_np_vec3(v.get("Array")) if v is not None else None)
    tangents: np.ndarray = XChild("Tangents", deserializer=lambda v: parse_np_vec4(v.get("Array")) if v is not None else None)
    tex_coords: np.ndarray = XChild("TexCoords", deserializer=lambda v: parse_np_vec3(v.get("Array")) if v is not None else None)
    indices: np.ndarray = XChild("Indices", deserializer=lambda v: parse_np_ivec3(v.get("Array")) if v is not None else None)


class DecalCommon(ObjectCommon):
    name: str = XAttr("Name")
    max_triangles: int = XAttr("MaxTriangles")
    offset: float = XAttr("Offset")
    sub_div: list[float] = XAttr("SubDiv", deserializer=parse_float_list)
    current_sub_div: int = XAttr("CurrentSubDiv")
    color: list[float] = XAttr("Color", deserializer=parse_float_list)
    material_index: int = XAttr("MaterialIndex")

    on_entity: bool = XAttr("OnEntity", deserializer=parse_bool)
    on_primitive: bool = XAttr("OnPrimitive", deserializer=parse_bool)
    on_static: bool = XAttr("OnStatic", deserializer=parse_bool)

    mesh: DecalMesh = XChild("DecalMesh")

    def as_dict(self):
        return {
            "id": self.id,
            "active": self.active,
            "color": self.color,
            "current_sub_div": self.current_sub_div,
            "material_index": self.material_index,
            "max_triangles": self.max_triangles,
            "name": self.name,
            "offset": self.offset,
            "on_entity": self.on_entity,
            "on_primitive": self.on_primitive,
            "on_static": self.on_static,
            "rotation": self.rotation,
            "scale": self.scale,
            "position": self.position,
            "sub_div": self.sub_div,
        }


class StaticObjectCommon(ObjectCommon):
    collides: bool = XAttr("Collides", deserializer=parse_bool)
    name: str = XAttr("Name")
    cast_shadows: bool = XAttr("CastShadows", deserializer=parse_bool)
    file_index: int = XAttr("FileIndex")

    def as_dict(self):
        return {
            "id": self.id,
            "cast_shadows": self.cast_shadows,
            "collides": self.collides,
            "file_index": self.file_index,
            "name": self.name,
            "rotation": self.rotation,
            "scale": self.scale,
            "position": self.position,
        }


class EntityCommon(ObjectCommon):
    name: str = XAttr("Name")
    file_index: int = XAttr("FileIndex")

    user_variables: dict[str, str] = XChild("UserVariables", deserializer=parse_user_variables)


class File(XmlAutoDeserialize):
    id: int = XAttr("Id")
    path: Path = XAttr("Path")
