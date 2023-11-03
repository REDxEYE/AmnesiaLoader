from pathlib import Path
from typing import Union

from AmnesiaLoader.resource_types.common import XmlAutoDeserialize, XChild, XAttr, parse_bool, parse_user_variables
from AmnesiaLoader.resource_types.hpl2.map import Light, Area
from AmnesiaLoader.resource_types.hpl_common.map import EntityCommon, ObjectCommon


class SubMesh(ObjectCommon):
    sub_mesh_id: int = XAttr("SubMeshId")
    name: str = XAttr("Name")


class Mesh(XmlAutoDeserialize):
    filename: Path = XAttr("Filename")
    submeshes: list[SubMesh] = XChild("SubMesh")


class ModelDataCommon(XmlAutoDeserialize):
    entities: list[Union[EntityCommon, Light, Area]]
    mesh: Mesh = XChild("Mesh")
