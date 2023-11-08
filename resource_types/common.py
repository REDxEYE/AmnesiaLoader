import struct
import reprlib
from enum import Enum
from itertools import chain
from typing import Tuple, BinaryIO, Optional, List, get_args, get_origin, get_type_hints, Type, Container, Union, \
    Iterable, Callable, Any
from xml.etree.ElementTree import Element
from dataclasses import dataclass, field

import numpy as np


class Vector2(Tuple[float, float]):
    @classmethod
    def from_string(cls, value: str):
        return cls(map(float, value.split(" ")))


class Vector3(Tuple[float, float, float]):
    @classmethod
    def from_string(cls, value: str):
        return cls(map(float, value.split(" ")))


class Vector4(Tuple[float, float, float, float]):
    @classmethod
    def from_string(cls, value: str):
        return cls(map(float, value.split(" ")))


Matrix = Tuple[Vector4, Vector4, Vector4, Vector3]


def read_fmt(fmt: str, file: BinaryIO):
    return struct.unpack(fmt, file.read(struct.calcsize(fmt)))


def read_u32(file: BinaryIO):
    return struct.unpack("I", file.read(4))[0]


def read_i32(file: BinaryIO):
    return struct.unpack("i", file.read(4))[0]


def read_u16(file: BinaryIO):
    return struct.unpack("H", file.read(2))[0]


def read_i16(file: BinaryIO):
    return struct.unpack("h", file.read(2))[0]


def read_u8(file: BinaryIO):
    return struct.unpack("B", file.read(1))[0]


def read_i8(file: BinaryIO):
    return struct.unpack("b", file.read(1))[0]


def read_f32(file: BinaryIO):
    return struct.unpack("f", file.read(4))[0]


def read_string(file: BinaryIO):
    buffer = b""
    while True:
        c = file.read(1)
        if c == b"\x00" or not c:
            break
        buffer += c
    return buffer.decode("utf8")


@dataclass(slots=True)
class XCommon:
    alias: str | None
    aliases: List[str] = field(default_factory=list)
    deserializer: Optional[Callable[[Any], Any]] = None

    @property
    def all_aliases(self):
        return [self.alias] + self.aliases


@dataclass(slots=True)
class XAttr(XCommon):
    deserializer: Optional[Callable[[str], Any]] = None
    default: Optional[Any] = None

    def __set_name__(self, owner, name):
        if self.alias is None:
            self.alias = name


@dataclass(slots=True)
class XChild(XCommon):
    deserializer: Optional[Callable[[Element], Any]] = None
    ignore_array: bool = False

    @classmethod
    def with_multiple_aliases(cls, *aliases, deserializer: Optional[Callable[[Element], Any]] = None,
                              ignore_array: bool = False):
        alias, *aliases = aliases
        return cls(alias, aliases, deserializer=deserializer, ignore_array=ignore_array)

    def __set_name__(self, owner, name):
        if self.alias is None:
            self.alias = name


SupportedTypes = Type[Union[int, float, bool, str, 'XmlAutoDeserialize']]

type_hints_cache = {}


class XmlAutoDeserialize:
    @staticmethod
    def _handle_item(item_type: SupportedTypes, value: Element):
        if value is None:
            return None
        if issubclass(item_type, XmlAutoDeserialize):
            value = item_type.from_xml(value)
        else:
            value = item_type(value.text)
        return value

    @classmethod
    def _handle_array(cls, item_type: Container[SupportedTypes], root: Element, xcommon: XCommon):
        items = []
        inner_type = get_args(item_type)[0]
        for item in chain(*[root.findall(name) for name in xcommon.all_aliases]):
            if xcommon.deserializer is not None:
                items.append(xcommon.deserializer(item))
            else:
                items.append(cls._handle_item(inner_type, item))
        return items

    @staticmethod
    def _find_first(root: Element, xcommon: XCommon) -> Element | None:
        names = set(xcommon.all_aliases)
        if root.tag in names:
            return root
        for elem in root:
            if elem.tag in names:
                return elem
        return None

    @staticmethod
    def _find_all(root: Element, names: List[str]) -> Iterable[Element]:
        for name in names:
            yield from root.findall(name)

    @classmethod
    def from_xml(cls, element: Element):
        if cls not in type_hints_cache:
            type_hints_cache[cls] = get_type_hints(cls)
        type_hints = type_hints_cache[cls]

        kwargs = {}
        for attr_name, attr_type in type_hints.items():
            xattr_descriptor = getattr(cls, attr_name, None)
            if xattr_descriptor is None:
                xattr_descriptor = XChild(attr_name)

            origin = get_origin(attr_type)
            if isinstance(xattr_descriptor, XChild):
                is_array = origin is not None and issubclass(origin,
                                                             (list, tuple)) and not xattr_descriptor.ignore_array
                if is_array:
                    kwargs[attr_name] = cls._handle_array(attr_type, element, xattr_descriptor)
                else:
                    value = cls._find_first(element, xattr_descriptor)
                    if xattr_descriptor.deserializer is not None:
                        kwargs[attr_name] = xattr_descriptor.deserializer(value)
                    else:
                        kwargs[attr_name] = cls._handle_item(attr_type, value)
                continue
            if isinstance(xattr_descriptor, XAttr):
                value = element.attrib.get(xattr_descriptor.alias, None)
                if value is None:
                    for alias in xattr_descriptor.aliases:
                        value = element.attrib.get(alias, None)
                        if value is not None:
                            break
                if value is None and xattr_descriptor.default is not None:
                    kwargs[attr_name] = xattr_descriptor.default
                elif value == "":
                    kwargs[attr_name] = None
                elif value is None:
                    kwargs[attr_name] = None
                elif xattr_descriptor.deserializer is not None:
                    kwargs[attr_name] = xattr_descriptor.deserializer(value)
                else:
                    kwargs[attr_name] = attr_type(value)
                continue

        def make_repr(fields, maxlevel=5):
            repr_instance = reprlib.Repr()
            repr_instance.maxlevel = maxlevel
            arepr = repr_instance.repr

            def __repr__(self):
                field_strs = ', '.join(f'{field}={repr(getattr(self, field))}' for field in fields)
                return f'{self.__class__.__name__}({field_strs})'

            return __repr__

        cls.__repr__ = make_repr(get_type_hints(cls).keys())
        obj = cls()
        obj.__dict__.update(kwargs)
        return obj


class Game(Enum):
    DARK_DESCENT = "The Dark Descent"
    MACHINE_FOR_PIGS = "Machine for Pigs"
    OTHER_HPL2 = "Other HPL2"
    SOMA = "SOMA"
    BUNKER = "The Bunker"
    OTHER_HPL3 = "Other HPL3"


def parse_float_list(value: str):
    return [float(v) for v in value.strip(" ").rstrip(" ").split(" ")]


def parse_int_list(value: str):
    return [int(v) for v in value.strip(" ").rstrip(" ").split(" ")]


def parse_bool(value: str):
    if value is None:
        return False
    value = value.lower()
    assert value in ["true", "false"]
    return value == "true"


def parse_np_vec3(value: str):
    return np.fromstring(value, np.float32, sep=" ").reshape((-1, 3))


def parse_np_vec4(value: str):
    return np.fromstring(value, np.float32, sep=" ").reshape((-1, 4))


def parse_np_ivec3(value: str):
    return np.fromstring(value, np.uint32, sep=" ").reshape((-1, 3))


def parse_user_variables(value: Element):
    data = {}
    for var in value:
        value_ = var.attrib["Value"]
        if value_ in ["false", "true"]:
            value_ = value_ == "true"
        elif value_ == "None":
            value_ = None
        elif value_.isdecimal():
            value_ = float(value_)
        elif value_.isnumeric():
            value_ = int(value_)
        data[var.attrib["Name"]] = value_
    return data


__all__ = [
    "Vector2", "Vector3", "Vector4", "Matrix",
    "read_fmt",
    "read_u32", "read_i32",
    "read_u16", "read_i16",
    "read_u8", "read_i8",
    "read_f32", "read_string",
    "XmlAutoDeserialize", "XChild", "XAttr",
    "Game",
    "parse_bool", "parse_float_list", "parse_np_ivec3",
    "parse_np_vec4", "parse_np_vec3", "parse_user_variables"
]
