"""Historical hit-location and wound generator for RPGs (data-driven)."""
from .model import load, DataError
from .engine import table_ranges, mechanism_ranges, compose_wound, roll_hit

__all__ = ["load", "DataError", "table_ranges", "mechanism_ranges", "compose_wound", "roll_hit"]
