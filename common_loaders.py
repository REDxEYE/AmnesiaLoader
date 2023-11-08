from typing import Optional

import bpy
from mathutils import Euler, Matrix, Vector

from .common_utils import get_or_create_collection
from .resource_types.common import Game
from .resource_types.hpl2.map import PointLight, SpotLight, BoxLight
from .resource_types.hpl_common.map import EntityCommon


def load_entity(entity, parent_object, entities_collection, game: Game,
                parent_collection: Optional[bpy.types.Collection] = None):
    if isinstance(entity, EntityCommon):
        entity_collection_instances = parent_collection or get_or_create_collection("EntitiesInstances",
                                                                                    bpy.context.scene.collection)

        obj = bpy.data.objects.new(entity.name, None)
        obj.empty_display_size = 1
        obj.instance_type = 'COLLECTION'
        obj.instance_collection = bpy.data.collections[entities_collection[entity.file_index]]
        entity_collection_instances.objects.link(obj)
        obj["entity_data"] = {}
        obj["entity_data"]["entity"] = entity.user_variables
        matrix = Matrix.LocRotScale(Vector(entity.position),
                                    Euler(entity.rotation),
                                    Vector(entity.scale))
        obj.hide_viewport = not entity.active
        obj.hide_render = not entity.active
        obj.matrix_local = matrix
        obj.parent = parent_object

    elif isinstance(entity, SpotLight):
        lights_collection = parent_collection or get_or_create_collection("Lights", bpy.context.scene.collection)

        light: bpy.types.SpotLight = bpy.data.lights.new(entity.name, 'SPOT')
        light.cycles.use_multiple_importance_sampling = True
        light.color = entity.diffuse_color[:3]
        light.energy = 100 * entity.radius
        light.spot_size = entity.fov
        obj: bpy.types.Object = bpy.data.objects.new(entity.name, light)
        lights_collection.objects.link(obj)
        obj["entity_data"] = {}
        obj["entity_data"]["entity"] = entity.as_dict()
        matrix = Matrix.LocRotScale(Vector(entity.position),
                                    Euler(entity.rotation),
                                    Vector(entity.scale))
        obj.hide_viewport = not entity.active
        obj.hide_render = not entity.active
        obj.matrix_local = matrix
        obj.parent = parent_object

    elif isinstance(entity, BoxLight):
        lights_collection = parent_collection or get_or_create_collection("Lights", bpy.context.scene.collection)

        light: bpy.types.SpotLight = bpy.data.lights.new(entity.name, 'AREA')
        light.cycles.use_multiple_importance_sampling = True
        light.color = entity.diffuse_color[:3]
        light.energy = 100 * entity.radius * Vector(entity.size).magnitude
        obj: bpy.types.Object = bpy.data.objects.new(entity.name, light)
        lights_collection.objects.link(obj)
        obj["entity_data"] = {}
        obj["entity_data"]["entity"] = entity.as_dict()
        matrix = Matrix.LocRotScale(Vector(entity.position),
                                    Euler(entity.rotation),
                                    Vector(entity.scale))
        obj.hide_viewport = not entity.active
        obj.hide_render = not entity.active
        obj.matrix_local = matrix
        obj.parent = parent_object

    elif isinstance(entity, PointLight):
        lights_collection = parent_collection or get_or_create_collection("Lights", bpy.context.scene.collection)

        light: bpy.types.SpotLight = bpy.data.lights.new(entity.name, 'POINT')
        light.cycles.use_multiple_importance_sampling = True
        light.color = entity.diffuse_color[:3]
        light.energy = 100 * entity.radius
        obj: bpy.types.Object = bpy.data.objects.new(entity.name, light)
        lights_collection.objects.link(obj)
        obj["entity_data"] = {}
        obj["entity_data"]["entity"] = entity.as_dict()
        matrix = Matrix.LocRotScale(Vector(entity.position),
                                    Euler(entity.rotation),
                                    Vector(entity.scale))
        obj.hide_viewport = not entity.active
        obj.hide_render = not entity.active
        obj.matrix_local = matrix
        obj.parent = parent_object
    else:
        print(f"Unsupported entity: {type(entity)}")