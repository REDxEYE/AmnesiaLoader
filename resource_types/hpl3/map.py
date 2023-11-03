import datetime
from pathlib import Path
from typing import Type, Any
from xml.etree.ElementTree import Element

import numpy as np

from AmnesiaLoader.resource_types.common import XmlAutoDeserialize, XChild, XAttr, parse_float_list, parse_bool, \
    parse_user_variables, parse_int_list, parse_np_vec3, parse_np_vec4
from AmnesiaLoader.resource_types.hpl2.map import File
from AmnesiaLoader.resource_types.hpl2.map import Light as LightHPL2
from AmnesiaLoader.resource_types.hpl2.map import PointLight as PointLightHPL2
from AmnesiaLoader.resource_types.hpl2.map import SpotLight as SpotLightHPL2
from AmnesiaLoader.resource_types.hpl2.map import BoxLight as BoxLightHPL2
from AmnesiaLoader.resource_types.hpl_common.map import PlaneCommon, ObjectCommon, DecalCommon, StaticObjectCommon, \
    EntityCommon


def _parse_array(o_type: Type[XmlAutoDeserialize]):
    def _parser(element: Element):
        items = []
        for item in element:
            items.append(o_type.from_xml(item))
        return items

    return _parser


def _parse_ts(value: str):
    return datetime.datetime.fromtimestamp(int(value))


class GlobalSettings(XmlAutoDeserialize):
    pass


class User(XmlAutoDeserialize):
    id: str = XAttr("ID")
    registration_time: str = XAttr("RegistrationTimestamp", deserializer=_parse_ts)


class RegisteredUsers(XmlAutoDeserialize):
    users: list[User] = XChild("User")


class HPLMap(XmlAutoDeserialize):
    global_settings: GlobalSettings = XChild("GlobalSettings")
    registered_users: RegisteredUsers = XChild("RegisteredUsers")


class _Object(ObjectCommon):
    uid: str = XAttr("UID")
    name: str = XAttr("Name")
    active: bool = XAttr("Active", deserializer=parse_bool, default=True)
    creation: datetime = XAttr("CreStamp", deserializer=_parse_ts)
    modification: datetime = XAttr("ModStamp", deserializer=_parse_ts)


class Area(_Object):
    area_type: str = XAttr("AreaType")
    mesh: Path = XAttr("Mesh")
    user_variables: dict[str, Any] = XChild("UserVariables", deserializer=parse_user_variables)


class Compound(_Object):
    components: list[int] = XChild("Component", deserializer=lambda v: int(v.get("ID")))


class Decal(DecalCommon, _Object):
    culled_by_distance: bool = XAttr("CulledByDistance", deserializer=parse_bool)
    culled_by_fog: bool = XAttr("CulledByFog", deserializer=parse_bool)
    static: bool = XAttr("Static", deserializer=parse_bool)
    angle_fade: list[float] = XAttr("AngleFade", deserializer=parse_float_list)

    def as_dict(self):
        d = super().as_dict()
        d.update({
            "culled_by_distance": self.culled_by_distance,
            "culled_by_fog": self.culled_by_fog,
            "static": self.static,
            "angle_fade": self.angle_fade,
        })
        return d


class Primitive(PlaneCommon, _Object):
    culled_by_distance: bool = XAttr("CulledByDistance", deserializer=parse_bool)
    culled_by_fog: bool = XAttr("CulledByFog", deserializer=parse_bool)
    diffuse_color_mul: list[float] = XAttr("DiffuseColorMul", deserializer=parse_float_list)


class StaticObject(StaticObjectCommon, _Object):
    is_occluder: bool = XAttr("IsOccluder", deserializer=parse_bool)
    color_mul: list[float] = XAttr("ColorMul", deserializer=parse_float_list)
    illum_color: list[float] = XAttr("IllumColor", deserializer=parse_float_list)
    illum_brightness: float = XAttr("IllumBrightness")
    culled_by_distance: bool = XAttr("CulledByDistance", deserializer=parse_bool)
    culled_by_fog: bool = XAttr("CulledByFog", deserializer=parse_bool)

    def as_dict(self):
        d = super().as_dict()
        d.update({
            "is_occluder": self.is_occluder,
            "color_mul": self.color_mul,
            "illum_color": self.illum_color,
            "illum_brightness": self.illum_brightness,
            "culled_by_distance": self.culled_by_distance,
            "culled_by_fog": self.culled_by_fog,
        })
        return d


class Entity(EntityCommon, _Object):
    important: bool = XAttr("Important", deserializer=parse_bool)
    static: bool = XAttr("Static", deserializer=parse_bool)
    culled_by_distance: bool = XAttr("CulledByDistance", deserializer=parse_bool)
    culled_by_fog: bool = XAttr("CulledByFog", deserializer=parse_bool)


class DetailMesh(XmlAutoDeserialize):
    file: Path = XAttr("File")
    ids: list[int] = XChild("DetailMeshEntityIDs", deserializer=lambda v: parse_int_list(v.text), ignore_array=True)
    positions: np.ndarray = XChild("DetailMeshEntityPositions", deserializer=lambda v: parse_np_vec3(v.text))
    rotations: np.ndarray = XChild("DetailMeshEntityRotations", deserializer=lambda v: parse_np_vec4(v.text))
    radii: np.ndarray = XChild("DetailMeshEntityRadii", deserializer=lambda v: parse_float_list(v.text))
    colors: np.ndarray = XChild("DetailMeshEntityColors", deserializer=lambda v: parse_np_vec3(v.text))
    mod_stamps: list[datetime.datetime] = XChild("DetailMeshEntityModStamps",
                                                 deserializer=lambda v: list(
                                                     map(datetime.datetime.fromtimestamp, parse_int_list(v.text))),
                                                 ignore_array=True)


class Light(_Object, LightHPL2):
    brightness: float = XAttr("Brightness")
    static: float = XAttr("Static", deserializer=parse_bool)


class PointLight(Light, PointLightHPL2):
    pass


class SpotLight(Light, SpotLightHPL2):
    pass


class BoxLight(Light, BoxLightHPL2):
    pass


def _parse_lights(entity_list: Element):
    entities = []
    for value in entity_list:
        tag = value.tag
        if tag == "PointLight":
            entities.append(PointLight.from_xml(value))
        elif tag == "SpotLight":
            entities.append(SpotLight.from_xml(value))
        elif tag == "BoxLight":
            entities.append(BoxLight.from_xml(value))
        else:
            print(f"Entity of type \"{tag}\" not supported")
    return entities


def parse_entity(entity_list: Element):
    entities = []
    for value in entity_list:
        tag = value.tag
        if tag == "Entity":
            entities.append(Entity.from_xml(value))
        elif tag == "Area":
            entities.append(Area.from_xml(value))
        elif tag == "PointLight":
            entities.append(PointLight.from_xml(value))
        elif tag == "SpotLight":
            entities.append(SpotLight.from_xml(value))
        elif tag == "BoxLight":
            entities.append(BoxLight.from_xml(value))
        elif tag == "Billboard":
            continue
        elif tag == "ParticleSystem":
            continue
        elif tag == "Sound":
            continue
        else:
            print(f"Entity of type \"{tag}\" not supported")
    return entities


class Section(XmlAutoDeserialize):
    name: str = XAttr("Name")


class StaticObjectSection(Section):
    files: list[File] = XChild("FileIndex_StaticObjects", deserializer=_parse_array(File), ignore_array=True)
    objects: list[StaticObject] = XChild("Objects", deserializer=_parse_array(StaticObject), ignore_array=True)


class EntitySection(Section):
    files: list[File] = XChild("FileIndex_Entities", deserializer=_parse_array(File), ignore_array=True)
    objects: list[Entity] = XChild("Objects", deserializer=_parse_array(Entity), ignore_array=True)


class DecalSection(Section):
    files: list[File] = XChild("FileIndex_Decals", deserializer=_parse_array(File), ignore_array=True)
    objects: list[Decal] = XChild("Objects", deserializer=_parse_array(Decal), ignore_array=True)


class AreaSection(Section):
    objects: list[Area] = XChild("Objects", deserializer=_parse_array(Area), ignore_array=True)


class CompoundSection(Section):
    objects: list[Compound] = XChild("Objects", deserializer=_parse_array(Compound), ignore_array=True)


class PrimitiveSection(Section):
    objects: list[Primitive] = XChild("Objects", deserializer=_parse_array(Primitive), ignore_array=True)


class LightSection(Section):
    objects: list[Light] = XChild("Objects", deserializer=_parse_lights, ignore_array=True)


class DetailMeshSection(Section):
    objects: list[DetailMesh] = XChild("DetailMesh")


class HPLMapTrackArea(XmlAutoDeserialize):
    sections: list[AreaSection] = XChild("Section")


class HPLMapTrackCompound(XmlAutoDeserialize):
    sections: list[CompoundSection] = XChild("Section")


class HPLMapTrackDecal(XmlAutoDeserialize):
    sections: list[DecalSection] = XChild("Section")


class HPLMapTrackPrimitive(XmlAutoDeserialize):
    sections: list[PrimitiveSection] = XChild("Section")


class HPLMapTrackStaticObject(XmlAutoDeserialize):
    sections: list[StaticObjectSection] = XChild("Section")


class HPLMapTrack_Entity(XmlAutoDeserialize):
    sections: list[EntitySection] = XChild("Section")


class HPLMapTrackLight(XmlAutoDeserialize):
    sections: list[LightSection] = XChild("Section")


class HPLMapTrackEntity(XmlAutoDeserialize):
    sections: list[EntitySection] = XChild("Section")


class HPLMapTrackDetailMeshes(XmlAutoDeserialize):
    sections: list[DetailMeshSection] = XChild("DetailMeshes",
                                               deserializer=lambda v: [DetailMeshSection.from_xml(g) for g in
                                                                       v.find("Sections")], ignore_array=True)
