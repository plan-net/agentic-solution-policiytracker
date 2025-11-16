"""Bundestag Vorgang Manager - Intelligent sync for legislative procedures."""
from .config import ManagerConfig
from .manager import BundestagVorgangManager

__all__ = ["BundestagVorgangManager", "ManagerConfig"]
