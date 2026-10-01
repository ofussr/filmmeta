"""Embedded metadata API. This package does not depend on Qt."""

from .reader import Metadata, read_files, read_one, register_namespace
from .writer import write_files, write_one

__all__ = [
    "Metadata",
    "read_one",
    "read_files",
    "register_namespace",
    "write_one",
    "write_files",
]
