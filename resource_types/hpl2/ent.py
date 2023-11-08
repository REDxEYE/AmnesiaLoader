from typing import Any, Union

from ..common import XmlAutoDeserialize, XChild, XAttr, parse_bool, parse_user_variables
from ..hpl2.common import EditorSession
from ..hpl2.map import parse_entity, Entity, Light, Area
from ..hpl_common.ent import ModelDataCommon


class ModelData(ModelDataCommon):
    entities: list[Union[Entity, Light, Area]] = XChild.with_multiple_aliases("Entities", deserializer=parse_entity,
                                                                              ignore_array=True)

class EntityFile(XmlAutoDeserialize):
    editor_session: EditorSession = XChild("EditorSession")
    user_variables: dict[str, Any] = XChild("UserDefinedVariables", deserializer=parse_user_variables)
    model_data: ModelData = XChild("ModelData")
