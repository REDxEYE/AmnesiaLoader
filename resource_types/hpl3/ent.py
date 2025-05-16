from typing import Any, Union

from UniLoader.common_api.xml_parsing import XmlAutoDeserialize, XChild, parse_user_variables
from ..hpl3.map import Entity, parse_entity
from ..hpl2.map import Light, Area
from ..hpl_common.ent import ModelDataCommon


class ModelData(ModelDataCommon):
    entities: list[Union[Entity, Light, Area]] = XChild.with_multiple_aliases("Entities", deserializer=parse_entity,
                                                                              ignore_array=True)


class EntityFile(XmlAutoDeserialize):
    model_data: ModelData = XChild("ModelData")
    user_variables: dict[str, Any] = XChild("UserDefinedVariables", deserializer=parse_user_variables)
