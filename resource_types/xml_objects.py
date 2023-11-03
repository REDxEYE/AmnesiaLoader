import abc
import datetime
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Type, TypeVar, Optional, Callable, Union, Tuple

import numpy as np

from AmnesiaLoader.resource_types.common import Vector3, Vector2, Vector4


class XMLObject(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_xml(cls, element: ET.Element):
        raise NotImplementedError(f"Class \"{cls.__name__}\" does not implement \"from_xml\" class method")


T = TypeVar("T", bound=XMLObject)


class XMLArray(List[T], XMLObject):
    type = XMLObject

    @classmethod
    def from_xml(cls, element: ET.Element):
        self = cls()
        for item in element:
            self.append(parse_xml_object(item, cls.type))
        return self


@dataclass(slots=True)
class GlobalSetting(XMLObject):
    name: str
    attributes: Dict[str, Any]
    children: List

    @classmethod
    def from_xml(cls, tree: ET.Element):
        attributes = dict(tree.attrib.items())
        children = []
        for item in tree:
            children.append((item.tag, item.attrib))
        return cls(tree.tag, attributes, children)


class GlobalSettings(List[GlobalSetting], XMLObject):
    @classmethod
    def from_xml(cls, tree: ET.Element):
        self = cls()
        for item in tree:
            self.append(GlobalSetting.from_xml(item))
        return self


@dataclass(slots=True)
class User(XMLObject):
    id: str
    registration_timestamp: datetime.datetime

    @classmethod
    def from_xml(cls, tree: ET.Element):
        return cls(tree.attrib["ID"], datetime.datetime.fromtimestamp(int(tree.attrib["RegistrationTimestamp"])))


class RegisteredUsers(List[User], XMLObject):

    @classmethod
    def from_xml(cls, tree: ET.Element):
        self = cls()
        for item in tree:
            self.append(User.from_xml(item))
        return self


@dataclass(slots=True)
class HPLMap(XMLObject):
    global_settings: GlobalSettings
    registered_users: RegisteredUsers

    @classmethod
    def from_xml(cls, tree: ET.Element):
        assert tree.tag == "HPLMap"

        global_settings = try_parse_xml_object(tree.find("GlobalSettings"), GlobalSettings, GlobalSettings)
        registered_users = try_parse_xml_object(tree.find("RegisteredUsers"), RegisteredUsers, RegisteredUsers)
        return cls(global_settings, registered_users)


@dataclass(slots=True)
class Var(XMLObject):
    object_id: int
    name: str
    value: str

    @classmethod
    def from_xml(cls, element: ET.Element):
        return cls(int(element.get("ObjectId", 0)), element.attrib["Name"], element.attrib["Value"])


class UserVariables(List[Var], XMLObject):
    @classmethod
    def from_xml(cls, element: ET.Element):
        self = cls()
        for item in element:
            self.append(parse_xml_object(item, Var))
        return self


@dataclass(slots=True)
class Area(XMLObject):
    id: int
    name: str
    creation_time: datetime.datetime
    modification_time: datetime.datetime
    position: Vector3
    rotation: Vector3
    scale: Vector3
    active: bool
    mesh: str
    uid: str
    area_type: str

    user_variables: UserVariables

    @classmethod
    def from_xml(cls, element: ET.Element):
        atribs = element.attrib
        assert atribs["Mesh"] == ""
        self = cls(
            int(atribs["ID"]),
            atribs["Name"],
            datetime.datetime.fromtimestamp(int(atribs["CreStamp"])),
            datetime.datetime.fromtimestamp(int(atribs["ModStamp"])),
            Vector3.from_string(atribs["WorldPos"]),
            Vector3.from_string(atribs["Rotation"]),
            Vector3.from_string(atribs["Scale"]),
            bool(atribs["Active"].title()),
            atribs["Mesh"],
            atribs["UID"],
            atribs["AreaType"],
            try_parse_xml_object(element.find("UserVariables"), UserVariables, UserVariables)
        )
        return self


class Objects(List[T], XMLObject):
    @classmethod
    def from_xml(cls, element: ET.Element):
        self = cls()
        for item in element:
            self.append(parse_xml_object(item, None))
        return self


class Section(List[T], XMLObject):

    def __init__(self, name: str):
        super().__init__()
        self.user = name

    @classmethod
    def from_xml(cls, element: ET.Element):
        self = cls(element.attrib["Name"])
        for item in element:
            self.append(parse_xml_object(item, None))
        return self


class HPLMapTrackArea(List[Section[Objects[Area]]], XMLObject):
    def __init__(self, uid: str, major_version: int, minor_version: int):
        super().__init__()
        self.id = uid
        self.major_version = major_version
        self.minor_version = minor_version

    @classmethod
    def from_xml(cls, element: ET.Element):
        assert element.tag == "HPLMapTrack_Area"
        if "MajorVersion" in element.attrib:
            self = cls(element.attrib["ID"], int(element.attrib["MajorVersion"]), int(element.attrib["MinorVersion"]))
        else:
            self = cls(element.attrib["ID"], *list(map(int, element.attrib["Version"].split("."))))
        for item in element:
            section = parse_xml_object(item, Section)
            self.append(section)
        return self


@dataclass(slots=True)
class Component(XMLObject):
    id: int

    @classmethod
    def from_xml(cls, element: ET.Element):
        atribs = element.attrib
        return cls(int(atribs["ID"]))


@dataclass(slots=True)
class Compound(XMLObject):
    id: int

    name: str
    creation_time: datetime.datetime
    modification_time: datetime.datetime

    position: Vector3
    rotation: Vector3
    scale: Vector3
    uid: str
    components: List[Component]

    @classmethod
    def from_xml(cls, element: ET.Element):
        components = []
        for elem in element:
            components.append(Component.from_xml(elem))
        atribs = element.attrib
        return cls(
            int(atribs["ID"]),
            atribs["Name"],
            datetime.datetime.fromtimestamp(int(atribs["CreStamp"]) & 0xFFFFFFFF),
            datetime.datetime.fromtimestamp(int(atribs["ModStamp"]) & 0xFFFFFFFF),
            Vector3.from_string(atribs["WorldPos"]),
            Vector3.from_string(atribs["Rotation"]),
            Vector3.from_string(atribs["Scale"]),
            atribs["UID"],
            components

        )


class HPLMapTrackCompound(List[Section[Objects[Compound]]], XMLObject):
    def __init__(self, uid: str, major_version: int, minor_version: int):
        super().__init__()
        self.id = uid
        self.major_version = major_version
        self.minor_version = minor_version

    @classmethod
    def from_xml(cls, element: ET.Element):
        assert element.tag == "HPLMapTrack_Compound"
        if "MajorVersion" in element.attrib:
            self = cls(element.attrib["ID"], int(element.attrib["MajorVersion"]), int(element.attrib["MinorVersion"]))
        else:
            self = cls(element.attrib["ID"], *list(map(int, element.attrib["Version"].split("."))))
        for item in element:
            section = parse_xml_object(item, Section)
            self.append(section)
        return self


@dataclass(slots=True)
class File(XMLObject):
    id: int
    path: Path

    @classmethod
    def from_xml(cls, element: ET.Element):
        return cls(int(element.attrib["Id"]), Path(element.attrib["Path"]))


class FileIndexDecals(XMLArray[File]):
    type = File


@dataclass(slots=True)
class DecalMesh(XMLObject):
    positions: Optional[np.ndarray] = None
    normals: Optional[np.ndarray] = None
    tangents: Optional[np.ndarray] = None
    uv: Optional[np.ndarray] = None
    indices: Optional[np.ndarray] = None

    @classmethod
    def from_xml(cls, element: ET.Element):
        self = cls()
        vertex_count = int(element.attrib["NumVerts"])
        for item in element:
            if item.tag == "Positions":
                self.positions = np.fromstring(item.attrib["Array"], sep=" ", dtype=np.float32).reshape(
                    (vertex_count, -1))
            elif item.tag == "Normals":
                self.normals = np.fromstring(item.attrib["Array"], sep=" ", dtype=np.float32).reshape(
                    (vertex_count, -1))
            elif item.tag == "Tangents":
                self.tangents = np.fromstring(item.attrib["Array"], sep=" ", dtype=np.float32).reshape(
                    (vertex_count, -1))
            elif item.tag == "TexCoords":
                self.uv = np.fromstring(item.attrib["Array"], sep=" ", dtype=np.float32).reshape((vertex_count, -1))
            elif item.tag == "Indices":
                self.indices = np.fromstring(item.attrib["Array"], sep=" ", dtype=np.uint32).reshape((-1, 3))
            else:
                raise NotImplementedError(f"Unsupported tag: {item.tag}")
        return self

    @property
    def empty(self):
        return self.positions is None


@dataclass(slots=True)
class Decal(XMLObject):
    id: int
    name: str
    creation_time: datetime.datetime
    modification_time: datetime.datetime

    position: Vector3
    rotation: Vector3
    scale: Vector3

    current_sub_div: int
    max_triangles: int
    angle_fade: Vector2
    offset: float
    terrain_offset: float
    sub_div: Vector2
    color: Vector4
    on_static: bool
    on_primitive: bool
    on_entity: bool
    material_index: int
    culled_by_distance: bool
    culled_by_fog: bool
    static: bool
    uid: str

    decal_mesh: DecalMesh

    @classmethod
    def from_xml(cls, element: ET.Element):
        atribs = element.attrib
        assert len(element) == 1
        decal_mesh = parse_xml_object(element[0], DecalMesh)
        return cls(
            int(atribs["ID"]),
            atribs["Name"],
            datetime.datetime.fromtimestamp(int(atribs["CreStamp"])),
            datetime.datetime.fromtimestamp(int(atribs["ModStamp"])),
            Vector3.from_string(atribs["WorldPos"]),
            Vector3.from_string(atribs["Rotation"]),
            Vector3.from_string(atribs["Scale"]),
            int(atribs["CurrentSubDiv"]),
            int(atribs["MaxTriangles"]),
            Vector2.from_string(atribs.get("AngleFade", "0 0")),
            float(atribs["Offset"]),
            float(atribs.get("TerrainOffset", 0)),
            Vector2.from_string(atribs["SubDiv"]),
            Vector3.from_string(atribs["Color"]),
            atribs["OnStatic"] == "true",
            atribs["OnPrimitive"] == "true",
            atribs["OnEntity"] == "true",
            int(atribs["MaterialIndex"]),
            atribs.get("CulledByDistance", "false") == "true",
            atribs.get("CulledByFog", "false") == "true",
            atribs.get("Static", "false") == "true",
            atribs["UID"],
            decal_mesh
        )


class HPLMapTrackDecal(List[Section[Union[FileIndexDecals, Objects[Decal]]]], XMLObject):
    def __init__(self, uid: str, major_version: int, minor_version: int):
        super().__init__()
        self.id = uid
        self.major_version = major_version
        self.minor_version = minor_version

    @classmethod
    def from_xml(cls, element: ET.Element):
        assert element.tag == "HPLMapTrack_Decal"
        if "MajorVersion" in element.attrib:
            self = cls(element.attrib["ID"], int(element.attrib["MajorVersion"]), int(element.attrib["MinorVersion"]))
        else:
            self = cls(element.attrib["ID"], *list(map(int, element.attrib["Version"].split("."))))
        for item in element:
            section = parse_xml_object(item, Section)
            self.append(section)
        return self


@dataclass(slots=True)
class Instance:
    id: int
    position: Vector3
    rotation: Vector4
    radius: float
    color: Vector4
    modification_time: datetime.datetime


@dataclass(slots=True)
class DetailMesh(XMLObject):
    model: Path

    instances: List[Instance] = field(default_factory=list)

    @classmethod
    def from_xml(cls, element: ET.Element):
        instances = []
        model_path = Path(element.attrib["File"])
        instance_count = int(element.attrib["NumOfInstances"])
        ids = np.fromstring(element.find("DetailMeshEntityIDs").text, sep=" ", dtype=np.uint32).reshape(
            (instance_count, -1))
        positions = np.fromstring(element.find("DetailMeshEntityPositions").text, sep=" ", dtype=np.float32).reshape(
            (instance_count, -1))
        rotations = np.fromstring(element.find("DetailMeshEntityRotations").text, sep=" ", dtype=np.float32).reshape(
            (instance_count, -1))
        radii = np.fromstring(element.find("DetailMeshEntityRadii").text, sep=" ", dtype=np.float32).reshape(
            (instance_count, -1))
        colors = np.fromstring(element.find("DetailMeshEntityColors").text, sep=" ", dtype=np.float32).reshape(
            (instance_count, -1))
        mod_stamps = np.fromstring(element.find("DetailMeshEntityModStamps").text, sep=" ", dtype=np.uint32).reshape(
            (instance_count, -1))
        for id_, position, rotation, radius, color, mod_stamp in zip(ids, positions, rotations, radii, colors,
                                                                     mod_stamps):
            instances.append(Instance(id_, position, rotation, radius, color, mod_stamp))
        return cls(model_path, instances)


class Sections(List[Section[T]], XMLObject):

    @classmethod
    def from_xml(cls, element: ET.Element):
        self = cls()
        for item in element:
            self.append(parse_xml_object(item, Section))
        return self


class DetailMeshes(List[Sections[DetailMesh]], XMLObject):

    @classmethod
    def from_xml(cls, element: ET.Element):
        self = cls()
        for item in element:
            self.append(parse_xml_object(item, Sections))
        return self


class HPLMapTrackDetailMeshes(List[DetailMeshes], XMLObject):

    def __init__(self, uid: str, major_version: int, minor_version: int):
        super().__init__()
        self.id = uid
        self.major_version = major_version
        self.minor_version = minor_version

    @classmethod
    def from_xml(cls, element: ET.Element):
        assert element.tag == "HPLMapTrack_DetailMeshes"
        if "MajorVersion" in element.attrib:
            self = cls(element.attrib["ID"], int(element.attrib["MajorVersion"]), int(element.attrib["MinorVersion"]))
        else:
            self = cls(element.attrib["ID"], *list(map(int, element.attrib["Version"].split("."))))
        for item in element:
            section = parse_xml_object(item, DetailMeshes)
            self.append(section)
        return self


@dataclass(slots=True)
class Plane:
    id: int
    name: str
    creation_time: datetime.datetime
    modification_time: datetime.datetime

    position: Vector3
    rotation: Vector4
    scale: Vector3

    material: Path
    start_corner: Vector3
    end_corner: Vector3
    cast_shadows: bool
    collides: bool
    diffuse_color_mul: Vector4

    culled_by_distance: bool
    culled_by_fog: bool
    tile_amount: Vector3
    tile_offset: Vector3
    texture_angle: float
    align_to_world_coords: bool

    uv_corners: Tuple[Vector2, Vector2, Vector2, Vector2]

    uid: str

    @classmethod
    def from_xml(cls, element: ET.Element):
        atribs = element.attrib
        return cls(
            int(atribs["ID"]),
            atribs["Name"],
            datetime.datetime.fromtimestamp(int(atribs["CreStamp"])),
            datetime.datetime.fromtimestamp(int(atribs["ModStamp"])),
            Vector3.from_string(atribs["WorldPos"]),
            Vector3.from_string(atribs["Rotation"]),
            Vector3.from_string(atribs["Scale"]),
            Path(atribs["Material"]),
            Vector3.from_string(atribs["StartCorner"]),
            Vector3.from_string(atribs["EndCorner"]),
            atribs["CastShadows"] == "true",
            atribs["Collides"] == "true",
            Vector4.from_string(atribs["DiffuseColorMul"]),
            atribs["CulledByDistance"] == "true",
            atribs["CulledByFog"] == "true",
            Vector3.from_string(atribs["TileAmount"]),
            Vector3.from_string(atribs["TileOffset"]),
            float(atribs["TextureAngle"]),
            atribs["AlignToWorldCoords"] == "true",
            (
                Vector2.from_string(atribs["Corner4UV"]), Vector2.from_string(atribs["Corner3UV"]),
                Vector2.from_string(atribs["Corner2UV"]), Vector2.from_string(atribs["Corner1UV"]),
            ),
            atribs["UID"]
        )


class HPLMapTrackPrimitive(List[Section[Objects[Plane]]], XMLObject):

    def __init__(self, uid: str, major_version: int, minor_version: int):
        super().__init__()
        self.id = uid
        self.major_version = major_version
        self.minor_version = minor_version

    @classmethod
    def from_xml(cls, element: ET.Element):
        assert element.tag == "HPLMapTrack_Primitive"
        if "MajorVersion" in element.attrib:
            self = cls(element.attrib["ID"], int(element.attrib["MajorVersion"]), int(element.attrib["MinorVersion"]))
        else:
            self = cls(element.attrib["ID"], *list(map(int, element.attrib["Version"].split("."))))
        for item in element:
            section = parse_xml_object(item, Section)
            self.append(section)
        return self


class FileIndexStaticObjects(XMLArray[File]):
    type = File


@dataclass(slots=True)
class StaticObject(XMLObject):
    id: int
    name: str
    creation_time: datetime.datetime
    modification_time: datetime.datetime

    position: Vector3
    rotation: Vector4
    scale: Vector3

    file_index: int
    cast_shadows: bool
    collides: bool
    is_occluder: bool
    color_mul: Vector4

    culled_by_distance: bool
    culled_by_fog: bool
    illum_color: Vector4
    illum_brightness: float
    uid: str

    @classmethod
    def from_xml(cls, element: ET.Element):
        atribs = element.attrib
        return cls(
            int(atribs["ID"]),
            atribs["Name"],
            datetime.datetime.fromtimestamp(int(atribs["CreStamp"])),
            datetime.datetime.fromtimestamp(int(atribs["ModStamp"])),
            Vector3.from_string(atribs["WorldPos"]),
            Vector3.from_string(atribs["Rotation"]),
            Vector3.from_string(atribs["Scale"]),
            int(atribs["FileIndex"]),
            atribs["Collides"] == "true",
            atribs["CastShadows"] == "true",
            atribs["IsOccluder"] == "true",
            Vector4.from_string(atribs["ColorMul"]),
            atribs["CulledByDistance"] == "true",
            atribs["CulledByFog"] == "true",
            Vector4.from_string(atribs["IllumColor"]),
            float(atribs["IllumBrightness"]),
            atribs["UID"]
        )


class HPLMapTrackStaticObject(List[Section[Union[FileIndexStaticObjects, Objects[StaticObject]]]], XMLObject):

    def __init__(self, uid: str, major_version: int, minor_version: int):
        super().__init__()
        self.id = uid
        self.major_version = major_version
        self.minor_version = minor_version

    @classmethod
    def from_xml(cls, element: ET.Element):
        assert element.tag == "HPLMapTrack_StaticObject"
        if "MajorVersion" in element.attrib:
            self = cls(element.attrib["ID"], int(element.attrib["MajorVersion"]), int(element.attrib["MinorVersion"]))
        else:
            self = cls(element.attrib["ID"], *list(map(int, element.attrib["Version"].split("."))))
        for item in element:
            section = parse_xml_object(item, Section)
            self.append(section)
        return self


@dataclass(slots=True)
class SubMesh(XMLObject):
    id: int
    name: str
    creation_time: datetime.datetime
    modification_time: datetime.datetime

    position: Vector3
    rotation: Vector4
    scale: Vector3

    tri_count: int
    material: Path
    static: bool


@dataclass(slots=True)
class Mesh(XMLObject):
    submeshes: List[SubMesh]


@dataclass(slots=True)
class ModelData(XMLObject):
    mesh: Mesh

    @classmethod
    def from_xml(cls, element: ET.Element):
        mesh = parse_xml_object(element.find("Mesh"), Mesh)
        return cls(mesh)


@dataclass(slots=True)
class Entity(XMLObject):
    model_data: ModelData
    user_variables: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_xml(cls, element: ET.Element):
        model_data = parse_xml_object(element.find("ModelData"), ModelData)
        user_variables = element.find("UserDefinedVariables")
        variables = {}
        for var in user_variables:
            variables[var.get("Name")] = var.get("Value")
        return cls(model_data, variables)


@dataclass(slots=True)
class Main(XMLObject):
    type: str
    depth_test: bool
    force_full_scale_textures: bool
    uv_sub_divs: Vector2
    use_alpha: bool
    physics_material: str
    blend_mode: str

    @classmethod
    def from_xml(cls, element: ET.Element):
        return cls(
            element.get("Type").lower(),
            element.get("DepthTest", "false") == "true",
            element.get("ForceFullScaleTextures", "false") == "true",
            Vector2.from_string(element.get("UVSubDivs", "1 1")),
            element.get("UseAlpha", "false") == "true",
            element.get("PhysicsMaterial"),
            element.get("BlendMode"),
        )


@dataclass(slots=True)
class Texture(XMLObject):
    type: str
    mipmaps: bool
    compressed: bool
    path: Path

    @classmethod
    def from_xml(cls, element: ET.Element):
        return cls(
            element.tag,
            element.get("MipMaps", "false") == "true",
            element.get("Compress", "false") == "true",
            Path(element.get("File"))
        )


@dataclass(slots=True)
class Material(XMLObject):
    main: Main
    textures: List[Texture]
    variables: Dict[str, str]

    @classmethod
    def from_xml(cls, element: ET.Element):
        main = parse_xml_object(element.find("Main"), Main)
        textures = []
        for item in element.find("TextureUnits"):
            textures.append(parse_xml_object(item, Texture))
        variables = {}
        for item in element.find("SpecificVariables"):
            variables[item.get("Name")] = item.get("Value")
        return cls(main, textures, variables)


class FileIndexEntities(XMLArray[File]):
    type = File


class MapEntity(XMLObject):
    pass


class HPLMapTrackEntity(List[Section[Union[FileIndexEntities, Objects[MapEntity]]]]):
    def __init__(self, uid: str, major_version: int, minor_version: int):
        super().__init__()
        self.id = uid
        self.major_version = major_version
        self.minor_version = minor_version

    @classmethod
    def from_xml(cls, element: ET.Element):
        assert element.tag == "HPLMapTrack_Entity"
        if "MajorVersion" in element.attrib:
            self = cls(element.attrib["ID"], int(element.attrib["MajorVersion"]), int(element.attrib["MinorVersion"]))
        else:
            self = cls(element.attrib["ID"], *list(map(int, element.attrib["Version"].split("."))))
        for item in element:
            section = parse_xml_object(item, Section)
            self.append(section)
        return self


SUPPORTED_OBJECTS: Dict[str, Type[XMLObject]] = {
    "HPLMap": HPLMap,
    "HPLMapTrack_Area": HPLMapTrackArea,
    "HPLMapTrack_Compound": HPLMapTrackCompound,
    "HPLMapTrack_Decal": HPLMapTrackDecal,
    "HPLMapTrack_DetailMeshes": HPLMapTrackDetailMeshes,
    "HPLMapTrack_Primitive": HPLMapTrackPrimitive,
    "HPLMapTrack_StaticObject": HPLMapTrackStaticObject,
    "HPLMapTrack_Entity": HPLMapTrackEntity,

    "FileIndex_Decals": FileIndexDecals,
    "FileIndex_StaticObjects": FileIndexStaticObjects,
    "FileIndex_Entities": FileIndexEntities,
    "GlobalSetting": GlobalSettings,
    "GlobalSettings": GlobalSettings,
    "User": User,
    "Area": Area,
    "Section": Section,
    "Sections": Sections,
    "Objects": Objects,
    "RegisteredUsers": RegisteredUsers,
    "UserVariables": UserVariables,
    "Var": Var,
    "Compound": Compound,
    "Component": Component,
    "Decal": Decal,
    "DecalMesh": DecalMesh,
    "File": File,
    "DetailMesh": DetailMesh,
    "DetailMeshes": DetailMeshes,
    "Plane": Plane,
    "StaticObject": StaticObject,

    # "Entity": Entity,
    "Entity": MapEntity,

    "ModelData": ModelData,
    "Mesh": Mesh,
    "SubMesh": SubMesh,
    "Material": Material,
    "Main": Main,

    "Diffuse": Texture,
    "NMap": Texture,
    "Alpha": Texture,
    "Specular": Texture,
    "Height": Texture,
    "DiffuseSide": Texture,
    "DiffuseTop": Texture,
    "DiffuseBottom": Texture,
    "NMapSide": Texture,
    "NMapTop": Texture,
    "NMapBottom": Texture,
    "SpecularSide": Texture,
    "SpecularTop": Texture,
    "SpecularBottom": Texture,
    "Diffuse_R": Texture,
    "Diffuse_G": Texture,
    "Diffuse_B": Texture,
    "Specular_R": Texture,
    "Specular_G": Texture,
    "Specular_B": Texture,
    "NMap_R": Texture,
    "NMap_G": Texture,
    "NMap_B": Texture,
    "DetailNMap": Texture,
    "HeightTop": Texture,
    "HeightSide": Texture,
    "HeightBottom": Texture,
    "CubeMap": Texture,
    "CubeMapAlpha": Texture,
    "Illumination": Texture,
    "DetailDiffuse": Texture,
    "Translucency": Texture,

}


def parse_xml_object(element: ET.Element, expected_type: Optional[Type[T]]) -> T:
    clazz = SUPPORTED_OBJECTS.get(element.tag, None)
    if clazz is None:
        raise NotImplementedError(f"Unsupported tag: {element.tag}")

    if expected_type is not None:
        assert clazz is expected_type, f"Expected {expected_type}, got {clazz}"
        return expected_type.from_xml(element)
    return clazz.from_xml(element)


def try_parse_xml_object(element: Optional[ET.Element], expected_type: Optional[Type[T]],
                         default_factory: Optional[Callable[[], XMLObject]]) -> Optional[T]:
    if element is None:
        if default_factory:
            return default_factory()
        return None
    return parse_xml_object(element, expected_type)
