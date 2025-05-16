from pathlib import Path
from typing import Union

from UniLoader.common_api.xml_parsing import XmlAutoDeserialize, XChild, XAttr
from ..hpl2.map import Light, Area
from ..hpl_common.map import EntityCommon, ObjectCommon


class SubMesh(ObjectCommon):
    sub_mesh_id: int = XAttr("SubMeshID", ["SubMeshId"])
    name: str = XAttr("Name")


class Mesh(XmlAutoDeserialize):
    filename: Path = XAttr("Filename")
    submeshes: list[SubMesh] = XChild("SubMesh")


class ModelDataCommon(XmlAutoDeserialize):
    entities: list[Union[EntityCommon, Light, Area]]
    mesh: Mesh = XChild("Mesh")
