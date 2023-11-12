import ctypes
import platform
import weakref
from ctypes import cdll
from enum import IntEnum, auto
from pathlib import Path
from typing import Optional


class UnsupportedSystem(Exception):
    pass


_platform_info = platform.uname()
_lib_path: Optional[Path] = Path(__file__).parent
if _platform_info.system == "Windows":
    _lib_path /= "TextureDecoder.dll"

elif _platform_info.system == 'Linux':
    _lib_path /= "libTextureDecoder.so"
else:
    raise UnsupportedSystem(f'System {_platform_info} not suppported')

assert _lib_path.exists()

_lib = cdll.LoadLibrary(_lib_path.as_posix())


# noinspection PyPep8Naming
class _Texture(ctypes.Structure):
    pass


class PixelFormat(IntEnum):
    INVALID = 0
    RGBA32 = auto()
    RGB32 = auto()
    RG32 = auto()
    R32 = auto()
    RGBA16 = auto()
    RGB16 = auto()
    RG16 = auto()
    R16 = auto()
    RGBA32F = auto()
    RGB32F = auto()
    RG32F = auto()
    R32F = auto()
    RGBA16F = auto()
    RGB16F = auto()
    RG16F = auto()
    R16F = auto()
    RGBA8888 = auto()
    RGB888 = auto()
    RG88 = auto()
    RA88 = auto()
    R8 = auto()
    RGB565 = auto()
    RGBA5551 = auto()
    BC1 = auto()
    BC1a = auto()
    BC2 = auto()
    BC3 = auto()
    BC4 = auto()
    BC5 = auto()
    BC6 = auto()
    BC7 = auto()


# int64_t get_buffer_size_from_texture(const sTexture *texture);
_lib.get_buffer_size_from_texture.argtypes = [ctypes.POINTER(_Texture)]
_lib.get_buffer_size_from_texture.restype = ctypes.c_int64

# int64_t get_buffer_size_from_texture_format(uint32_t width, uint32_t height, ePixelFormat pixelFormat);
_lib.get_buffer_size_from_texture_format.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint16]
_lib.get_buffer_size_from_texture_format.restype = ctypes.c_int64

# sTexture *create_texture(const uint8_t *data, size_t dataSize, uint32_t width, uint32_t height, ePixelFormat pixelFormat);
_lib.create_texture.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32,
                                ctypes.c_uint16]
_lib.create_texture.restype = ctypes.POINTER(_Texture)

# sTexture *create_empty_texture(uint32_t width, uint32_t height, ePixelFormat pixelFormat);
_lib.create_empty_texture.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint16]
_lib.create_empty_texture.restype = ctypes.POINTER(_Texture)

# bool convert_texture(const sTexture *from_texture, sTexture *to_texture);
_lib.convert_texture.argtypes = [ctypes.POINTER(_Texture), ctypes.POINTER(_Texture)]
_lib.convert_texture.restype = ctypes.c_bool

# bool get_texture_data(const sTexture *texture, char *buffer, uint32_t buffer_size);
_lib.get_texture_data.argtypes = [ctypes.POINTER(_Texture), ctypes.c_char_p, ctypes.c_uint32]
_lib.get_texture_data.restype = ctypes.c_bool

# uint32_t get_texture_width(const sTexture *texture);
_lib.get_texture_width.argtypes = [ctypes.POINTER(_Texture)]
_lib.get_texture_width.restype = ctypes.c_uint32

# uint32_t get_texture_height(const sTexture *texture);
_lib.get_texture_height.argtypes = [ctypes.POINTER(_Texture)]
_lib.get_texture_height.restype = ctypes.c_uint32

# ePixelFormat get_texture_pixel_format(const sTexture *texture);
_lib.get_texture_pixel_format.argtypes = [ctypes.POINTER(_Texture)]
_lib.get_texture_pixel_format.restype = ctypes.c_uint16

# void free_texture(sTexture *texture);
_lib.free_texture.argtypes = [ctypes.POINTER(_Texture)]
_lib.free_texture.restype = None

# sTexture *load_dds(char *filename);
_lib.load_dds.argtypes = [ctypes.c_char_p]
_lib.load_dds.restype = ctypes.POINTER(_Texture)

# sTexture *load_png(const char *filename, int expected_channels);
_lib.load_png.argtypes = [ctypes.c_char_p, ctypes.c_int]
_lib.load_png.restype = ctypes.POINTER(_Texture)

# sTexture *load_tga(const char *filename, int expected_channels);
_lib.load_tga.argtypes = [ctypes.c_char_p, ctypes.c_int]
_lib.load_tga.restype = ctypes.POINTER(_Texture)

# bool write_png(const char *filename, const sTexture* texture);
_lib.write_png.argtypes = [ctypes.c_char_p, ctypes.POINTER(_Texture)]
_lib.write_png.restype = ctypes.c_bool

# bool write_tga(const char *filename, const sTexture* texture);
_lib.write_tga.argtypes = [ctypes.c_char_p, ctypes.POINTER(_Texture)]
_lib.write_tga.restype = ctypes.c_bool

# sTexture *load_hdr(const char *filename);
_lib.load_hdr.argtypes = [ctypes.c_char_p]
_lib.load_hdr.restype = ctypes.POINTER(_Texture)


class Texture:
    def __init__(self, p):
        self.ptr = p

    def __del__(self):
        _lib.free_texture(self.ptr)

    @classmethod
    def from_dds(cls, path: Path) -> 'Texture':
        return cls(_lib.load_dds(str(path).encode("utf8")))

    @classmethod
    def new_empty(cls, width: int, height: int, pixel_format: PixelFormat) -> 'Texture':
        return cls(_lib.create_empty_texture(width, height, pixel_format))

    @property
    def width(self) -> int:
        return _lib.get_texture_width(self.ptr)

    @property
    def height(self) -> int:
        return _lib.get_texture_height(self.ptr)

    @property
    def pixel_format(self) -> PixelFormat:
        return PixelFormat(_lib.get_texture_pixel_format(self.ptr))

    @property
    def data(self) -> Optional[bytes]:
        buffer_size = _lib.get_buffer_size_from_texture(self.ptr)
        buffer = bytes(buffer_size)
        if _lib.get_texture_data(self.ptr, buffer, buffer_size):
            return buffer
        return None

    def convert_to(self, pixel_format: PixelFormat) -> Optional['Texture']:
        new = self.new_empty(self.width, self.height, pixel_format)
        if _lib.convert_texture(self.ptr, new.ptr):
            return new
        return None

    def write_png(self, filepath: Path):
        if not _lib.write_png(str(filepath).encode("utf8"), self.ptr):
            raise ValueError("Failed to save png")

    def write_tga(self, filepath: Path):
        if not _lib.write_tga(str(filepath).encode("utf8"), self.ptr):
            raise ValueError("Failed to save tga")
