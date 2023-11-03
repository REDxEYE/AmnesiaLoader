from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import List, Optional, BinaryIO, Tuple

import numpy as np

from .common import *


@dataclass(slots=True)
class Bone:
    name: str
    unk_name: str
    matrix: Matrix
    children: List['Bone'] = field(default_factory=list)

    @classmethod
    def from_file(cls, file: BinaryIO):
        name = read_string(file)
        unk_name = read_string(file)
        matrix = (read_fmt("4f", file), read_fmt("4f", file), read_fmt("4f", file), read_fmt("4f", file))
        child_count = read_u32(file)
        children = [Bone.from_file(file) for _ in range(child_count)]
        return cls(name, unk_name, matrix, children)

    def flatten(self) -> List[Tuple['Bone', str]]:
        pairs = []
        for child in self.children:
            pairs.append((child, self.name))
            pairs.extend(child.flatten())
        return pairs


@dataclass(slots=True)
class Skeleton:
    bones: List[Bone] = field(default_factory=list)

    @classmethod
    def from_file(cls, file: BinaryIO):
        bone_count = read_u32(file)
        return cls([Bone.from_file(file) for _ in range(bone_count)])

    def flatten_bones(self):
        bones = []
        for bone in self.bones:
            bones.append((bone, None))
            bones.extend(bone.flatten())
        return bones


@dataclass(slots=True)
class Node:
    name: str
    matrix: Matrix
    unk_0: int

    children: List['Node'] = field(default_factory=list)

    @classmethod
    def from_file(cls, file: BinaryIO):
        name = read_string(file)
        matrix = (read_fmt("4f", file), read_fmt("4f", file), read_fmt("4f", file), read_fmt("4f", file))
        unk_0 = read_u32(file)
        child_count = read_u32(file)
        children = [Node.from_file(file) for _ in range(child_count)]
        return cls(name, matrix, unk_0, children)

    def flatten(self) -> List[Tuple[str, Optional[str]]]:
        pairs = []
        for child in self.children:
            pairs.append((child, self.name))
            pairs.extend(child.flatten())
        return pairs


@dataclass(slots=True)
class Collider:
    unk_0: int
    matrix: Matrix
    unk_vec: Vector3
    unk_1: int

    @classmethod
    def from_file(cls, file: BinaryIO):
        unk_0 = read_u16(file)
        matrix = (read_fmt("4f", file), read_fmt("4f", file), read_fmt("4f", file), read_fmt("4f", file))
        unk_vec = read_fmt("3f", file)
        unk_1 = read_u8(file)

        return cls(unk_0, matrix, unk_vec, unk_1)


VertexBonePair = np.dtype(
    [
        ("vtx_id", np.uint32),
        ("bone_id", np.uint32),
        ("weight", np.float32),
    ]
)


class VertexBufferElement(IntEnum):
    Normal = 0
    Position = 1
    Color0 = 2
    Color1 = 3
    Texture1Tangent = 4
    Texture0 = 5
    Texture1 = 6
    Texture2 = 7
    Texture3 = 8
    Texture4 = 9
    User0 = 10
    User1 = 11
    User2 = 12
    User3 = 13


class VertexBufferElementFormat(IntEnum):
    Float = 0
    Int = 1
    Byte = 2


@dataclass(slots=True)
class VtxBufferDesc:
    usage: VertexBufferElement
    format: VertexBufferElementFormat
    shader_program_var: int
    component_count: int

    @classmethod
    def from_file(cls, file: BinaryIO):
        usage, fmt, unk_2, component_count = read_fmt("2H2I", file)
        return cls(VertexBufferElement(usage), VertexBufferElementFormat(fmt), unk_2, component_count)


@dataclass(slots=True)
class SubMesh:
    name: str
    material: Path
    matrix: Matrix
    unk_vec: Vector3
    unk: int

    colliders: List[Collider] = field(default_factory=list)
    weights: np.ndarray = field(default_factory=list)
    vertex_buffers_desc: List[VtxBufferDesc] = field(default_factory=list)
    vertex_buffers: List[bytes] = field(default_factory=list)
    lods: List[Tuple[float, np.ndarray]] = field(default_factory=list)

    @classmethod
    def from_file(cls, file: BinaryIO, version: int = 8):
        name = read_string(file)
        material = Path(read_string(file))
        matrix = (read_fmt("4f", file), read_fmt("4f", file), read_fmt("4f", file), read_fmt("4f", file))
        unk_vec = read_fmt("3f", file)
        unk = read_u8(file)

        collider_count = read_u32(file)
        colliders = [Collider.from_file(file) for _ in range(collider_count)]

        vertex_bone_pairs_count = read_u32(file)
        weights = np.frombuffer(file.read(vertex_bone_pairs_count * VertexBonePair.itemsize), dtype=VertexBonePair)

        vertex_count_count = read_u32(file)
        vertex_buffer_count = read_u32(file)

        descs = []
        buffers = []

        for _ in range(vertex_buffer_count):
            desc = VtxBufferDesc.from_file(file)
            descs.append(desc)
            buffers.append(file.read(vertex_count_count * 4 * desc.component_count))

        lods = []
        if version == 8:
            lod_count = read_u32(file)
            for _ in range(lod_count):
                index_count = read_u32(file)
                switch_distance = read_f32(file)
                indices = np.frombuffer(file.read(index_count * 4), np.uint32).reshape((-1, 3))
                lods.append((switch_distance, indices))
        else:
            index_count = read_u32(file)
            indices = np.frombuffer(file.read(index_count * 4), np.uint32).reshape((-1, 3))
            lods.append((0.0, indices))
        return cls(name, material, matrix, unk_vec, unk, colliders, weights, descs, buffers, lods)

    def _get_data(self, usage: VertexBufferElement) -> Optional[np.ndarray]:
        for desc, buffer in zip(self.vertex_buffers_desc, self.vertex_buffers):
            if desc.usage == usage and usage == VertexBufferElement.Normal:
                return np.frombuffer(buffer, np.float32).reshape((-1, desc.component_count))[:, :3]
            elif desc.usage == usage and usage == VertexBufferElement.Position:
                return np.frombuffer(buffer, np.float32).reshape((-1, desc.component_count))[:, :3]
            elif desc.usage == usage and usage == VertexBufferElement.Color0:
                return np.frombuffer(buffer, np.float32).reshape((-1, desc.component_count))[:, :4]
            elif desc.usage == usage and usage == VertexBufferElement.Color1:
                return np.frombuffer(buffer, np.float32).reshape((-1, desc.component_count))[:, :4]
            elif desc.usage == usage and usage == VertexBufferElement.Texture1Tangent:
                return np.frombuffer(buffer, np.float32).reshape((-1, desc.component_count))[:, :4]
            elif desc.usage == usage and usage == VertexBufferElement.Texture0:
                return np.frombuffer(buffer, np.float32).reshape((-1, desc.component_count))[:, :2]
            elif desc.usage == usage and usage == VertexBufferElement.Texture1:
                return np.frombuffer(buffer, np.float32).reshape((-1, desc.component_count))[:, :2]
            elif desc.usage == usage and usage == VertexBufferElement.Texture2:
                return np.frombuffer(buffer, np.float32).reshape((-1, desc.component_count))[:, :2]
            elif desc.usage == usage and usage == VertexBufferElement.Texture3:
                return np.frombuffer(buffer, np.float32).reshape((-1, desc.component_count))[:, :2]
            elif desc.usage == usage and usage == VertexBufferElement.Texture4:
                return np.frombuffer(buffer, np.float32).reshape((-1, desc.component_count))[:, :2]
        return None

    @property
    def position_data(self) -> Optional[np.ndarray]:
        return self._get_data(VertexBufferElement.Position)

    def uv_data(self, layer: int = 0) -> Optional[np.ndarray]:
        return self._get_data(VertexBufferElement.Texture0 + layer)

    def uv1_tangent_data(self) -> Optional[np.ndarray]:
        return self._get_data(VertexBufferElement.Texture1Tangent)

    @property
    def normal_data(self) -> Optional[np.ndarray]:
        return self._get_data(VertexBufferElement.Normal)

    def color_data(self, layer: int = 0) -> Optional[np.ndarray]:
        return self._get_data(VertexBufferElement.Color0 + layer)

    def lod_indices(self, lod_id):
        if lod_id > len(self.lods):
            lod_id = len(self.lods) - 1
        return self.lods[lod_id][1]


@dataclass(slots=True)
class Msh:
    version: int
    flags: int
    unused: int
    skeleton: Optional[Skeleton] = None

    nodes: List[Node] = field(default_factory=list)

    submeshes: List[SubMesh] = field(default_factory=list)

    # animations: List[Animation] = field(default_factory=list)

    @classmethod
    def from_file(cls, file: BinaryIO):
        magic = read_u32(file)
        assert magic == 0x76034569, "Invalid magic"
        version = read_u32(file)
        assert version in (7, 8), "Unsupported version"
        flags = 0
        if version == 8:
            flags = read_u32(file)
        submesh_count = read_u32(file)
        unused = read_u32(file)
        has_skeleton = read_u8(file)

        skeleton = None
        if has_skeleton:
            skeleton = Skeleton.from_file(file)

        nodes_count = read_u32(file)
        nodes = [Node.from_file(file) for _ in range(nodes_count)]
        submeshes = [SubMesh.from_file(file, version) for _ in range(submesh_count)]
        animation_count = read_u32(file)
        if animation_count > 0:
            read_string(file)
            duration, tracks, bboxes = read_fmt("f2I", file)
            if bboxes > 0:
                print("AAAAAA")
        return cls(version, flags, unused, skeleton, nodes, submeshes)
