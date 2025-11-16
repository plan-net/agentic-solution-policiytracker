"""Bundestag Aktivitaet Manager - Intelligent sync for parliamentary documents."""
from .config import ManagerConfig
from .manager import BundestagAktivitaetManager

__all__ = ["BundestagAktivitaetManager", "ManagerConfig"]
