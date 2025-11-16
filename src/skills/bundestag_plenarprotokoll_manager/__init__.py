"""Bundestag Plenarprotokoll Manager - Intelligent sync for parliamentary documents."""
from .config import ManagerConfig
from .manager import BundestagPlenarprotokollManager

__all__ = ["BundestagPlenarprotokollManager", "ManagerConfig"]
