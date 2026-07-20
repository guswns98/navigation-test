from gpx_generator.generator import fetch_route, generate_gpx
from gpx_generator.interpolate import interpolate_route
from gpx_generator.mutations import apply_detour, apply_overspeed, apply_stop

__all__ = [
    "fetch_route",
    "generate_gpx",
    "interpolate_route",
    "apply_detour",
    "apply_stop",
    "apply_overspeed",
]
