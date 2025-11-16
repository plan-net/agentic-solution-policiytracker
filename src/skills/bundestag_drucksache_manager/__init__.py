"""Bundestag Drucksache Manager - Intelligent sync for parliamentary documents."""
from .config import ManagerConfig
from .manager import BundestagDrucksacheManager

__all__ = ["BundestagDrucksacheManager", "ManagerConfig"]
