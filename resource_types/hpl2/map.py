from pathlib import Path
from typing import Union
from xml.etree.ElementTree import Element

from AmnesiaLoader.resource_types.common import XmlAutoDeserialize, XChild, XAttr, parse_float_list, parse_bool, \
    parse_user_variables
from AmnesiaLoader.resource_types.hpl2.common import EditorSession
from AmnesiaLoader.resource_types.hpl_common.map import PlaneCommon, DecalCommon, File, StaticObjectCommon, EntityCommon


class FileList(XmlAutoDeserialize):
    files: list[File] = XChild("File")


class StaticObject(StaticObjectCommon):
    group: int = XAttr("Group")
    tag: str = XAttr("Tag")

    def as_dict(self):
        d = super().as_dict()
        d.update({
            "group": self.group,
            "tag": self.tag,
        })
        return d


class StaticObjects(XmlAutoDeserialize):
    objects: list[StaticObject] = XChild("StaticObject")


class Plane(PlaneCommon):
    group: int = XAttr("Group")
    tag: str = XAttr("Tag")


class Primitives(XmlAutoDeserialize):
    planes: list[Plane] = XChild("Plane")


class Decal(DecalCommon):
    group: int = XAttr("Group")
    tag: str = XAttr("Tag")

    def as_dict(self):
        d = super().as_dict()
        d.update({
            "group": self.group,
            "tag": self.tag,
        })
        return d


class Decals(XmlAutoDeserialize):
    decals: list[Decal] = XChild("Decal")


class Entity(EntityCommon):
    active: bool = XAttr("Active", deserializer=parse_bool)
    group: int = XAttr("Group")
    tag: str = XAttr("Tag")


class Light(XmlAutoDeserialize):
    id: int = XAttr("ID")
    group: int = XAttr("Group")
    name: str = XAttr("Name")
    active: bool = XAttr("Active", deserializer=parse_bool)
    rotation: list[float] = XAttr("Rotation", deserializer=parse_float_list)
    scale: list[float] = XAttr("Scale", deserializer=parse_float_list)
    position: list[float] = XAttr("WorldPos", deserializer=parse_float_list)
    cast_shadows: bool = XAttr("CastShadows", deserializer=parse_bool, default=False)
    diffuse_color: list[float] = XAttr("DiffuseColor", deserializer=parse_float_list, default=[1, 1, 1, 1])
    radius: float = XAttr("Radius")
    falloff_map: Path = XAttr("FalloffMap", default=None)
    flicker_active: bool = XAttr("FlickerActive", deserializer=parse_bool, default=None)
    flicker_fade: bool = XAttr("FlickerFade", deserializer=parse_bool, default=None)
    flicker_off_color: list[float] = XAttr("FlickerOffColor", deserializer=parse_float_list, default=[0, 0, 0, 1])
    flicker_off_fade_max_length: float = XAttr("FlickerOffFadeMaxLength", default=None)
    flicker_off_fade_min_length: float = XAttr("FlickerOffFadeMinLength", default=None)
    flicker_off_max_length: float = XAttr("FlickerOffMaxLength", default=None)
    flicker_off_min_length: float = XAttr("FlickerOffMinLength", default=None)
    flicker_on_fade_max_length: float = XAttr("FlickerOnFadeMaxLength", default=None)
    flicker_on_fade_min_length: float = XAttr("FlickerOnFadeMinLength", default=None)
    flicker_off_radius: float = XAttr("FlickerOffRadius", default=None)
    flicker_on_max_length: float = XAttr("FlickerOnMaxLength", default=None)
    flicker_on_min_length: float = XAttr("FlickerOnMinLength", default=None)
    flicker_off_sound: Path = XAttr("FlickerOffSound", default=None)
    flicker_on_ps: Path = XAttr("FlickerOnPS", default=None)
    flicker_on_sound: Path = XAttr("FlickerOnSound", default=None)
    gobo: Path = XAttr("Gobo", default=None)
    gobo_anim_frame_time: float = XAttr("GoboAnimFrameTime", default=None)
    gobo_anim_mode: str = XAttr("GoboAnimMode", default=None)
    shadow_resolution: str = XAttr("ShadowResolution", default="High")
    shadows_affect_dynamic: bool = XAttr("ShadowsAffectDynamic", default=True, deserializer=parse_bool)
    shadows_affect_static: bool = XAttr("ShadowsAffectStatic", default=True, deserializer=parse_bool)
    tag: str = XAttr("Tag")

    def as_dict(self):
        return {
            "id": self.id,
            "group": self.group,
            "name": self.name,
            "active": self.active,
            "rotation": self.rotation,
            "scale": self.scale,
            "position": self.position,
            "cast_shadows": self.cast_shadows,
            "diffuse_color": self.diffuse_color,
            "radius": self.radius,
            "falloff_map": str(self.falloff_map),
            "flicker_active": self.flicker_active,
            "flicker_fade": self.flicker_fade,
            "flicker_off_color": self.flicker_off_color,
            "flicker_off_fade_max_length": self.flicker_off_fade_max_length,
            "flicker_off_fade_min_length": self.flicker_off_fade_min_length,
            "flicker_off_max_length": self.flicker_off_max_length,
            "flicker_off_min_length": self.flicker_off_min_length,
            "flicker_on_fade_max_length": self.flicker_on_fade_max_length,
            "flicker_on_fade_min_length": self.flicker_on_fade_min_length,
            "flicker_off_radius": self.flicker_off_radius,
            "flicker_on_max_length": self.flicker_on_max_length,
            "flicker_on_min_length": self.flicker_on_min_length,
            "flicker_off_sound": str(self.flicker_off_sound),
            "flicker_on_ps": str(self.flicker_on_ps),
            "flicker_on_sound": str(self.flicker_on_sound),
            "gobo": str(self.gobo),
            "gobo_anim_frame_time": self.gobo_anim_frame_time,
            "gobo_anim_mode": self.gobo_anim_mode,
            "shadow_resolution": self.shadow_resolution,
            "shadows_affect_dynamic": self.shadows_affect_dynamic,
            "shadows_affect_static": self.shadows_affect_static,
            "tag": self.tag,
        }


class SpotLight(Light, XmlAutoDeserialize):
    aspect: float = XAttr("Aspect")
    fov: float = XAttr("FOV")
    near_clip_plane: float = XAttr("NearClipPlane")

    def as_dict(self):
        d = super().as_dict()
        d.update({
            "aspect": self.aspect,
            "fov": self.fov,
            "near_clip_plane": self.near_clip_plane,
        })
        return d


class BoxLight(Light, XmlAutoDeserialize):
    size: list[float] = XAttr("Size", deserializer=parse_float_list)

    def as_dict(self):
        d = super().as_dict()
        d.update({
            "size": self.size,
        })
        return d


class PointLight(Light, XmlAutoDeserialize):
    pass


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


class Area(XmlAutoDeserialize):
    id: int = XAttr("ID")
    group: int = XAttr("Group")
    name: str = XAttr("Name")
    active: bool = XAttr("Active", deserializer=parse_bool)
    rotation: list[float] = XAttr("Rotation", deserializer=parse_float_list)
    scale: list[float] = XAttr("Scale", deserializer=parse_float_list)
    position: list[float] = XAttr("WorldPos", deserializer=parse_float_list)
    area_type: str = XAttr("AreaType")
    Mesh: Path = XAttr("AreaType")

    user_variables: dict[str, str] = XChild("UserVariables", deserializer=parse_user_variables)


class MapContents(XmlAutoDeserialize):
    file_index_static_objects: FileList = XChild("FileIndex_StaticObjects")
    file_index_entities: FileList = XChild("FileIndex_Entities")
    file_index_decals: FileList = XChild("FileIndex_Decals")
    static_objects: StaticObjects = XChild("StaticObjects")
    primitives: Primitives = XChild("Primitives")
    decals: Decals = XChild("Decals")
    entities: list[Union[Entity, Light, Area]] = XChild.with_multiple_aliases("Entities",
                                                                              deserializer=parse_entity,
                                                                              ignore_array=True)
    # misc: Misc = XChild("Misc")
    # static_object_combos: StaticObjectCombos = XChild("StaticObjectCombos")


class MapData(XmlAutoDeserialize):
    fog_active: bool = XAttr("FogActive", deserializer=parse_bool)
    fog_color: list[float] = XAttr("FogColor", deserializer=parse_float_list)
    fog_culling: bool = XAttr("FogCulling", deserializer=parse_bool)
    fog_end: float = XAttr("FogEnd")
    fog_falloff_exp: float = XAttr("FogFalloffExp")
    fog_start: float = XAttr("FogStart")
    global_decal_max_tris: int = XAttr("GlobalDecalMaxTris")
    name: str = XAttr("Name")
    sky_box_active: bool = XAttr("SkyBoxActive", deserializer=parse_bool)
    sky_box_color: list[float] = XAttr("SkyBoxColor", deserializer=parse_float_list)
    sky_box_texture: str = XAttr("SkyBoxTexture")

    map_contents: MapContents = XChild("MapContents")


class Level(XmlAutoDeserialize):
    editor_session: EditorSession = XChild("EditorSession")
    map_data: MapData = XChild("MapData")


class HPL2Map(XmlAutoDeserialize):
    level: Level = XChild("Level")
