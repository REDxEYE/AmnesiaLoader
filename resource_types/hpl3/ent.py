from typing import Any, Union

from AmnesiaLoader.resource_types.common import XmlAutoDeserialize, XChild, parse_user_variables
from AmnesiaLoader.resource_types.hpl3.map import Entity, parse_entity
from AmnesiaLoader.resource_types.hpl2.map import Light, Area
from AmnesiaLoader.resource_types.hpl_common.ent import ModelDataCommon


class ModelData(ModelDataCommon):
    entities: list[Union[Entity, Light, Area]] = XChild.with_multiple_aliases("Entities", deserializer=parse_entity,
                                                                              ignore_array=True)


class EntityFile(XmlAutoDeserialize):
    model_data: ModelData = XChild("ModelData")
    user_variables: dict[str, Any] = XChild("UserDefinedVariables", deserializer=parse_user_variables)
