"""Shared Minecraft face coordinates; UV origin is the top left of a texture."""

import math

DIRECTIONS = {
    "up": [0, 1, 0],
    "down": [0, -1, 0],
    "north": [0, 0, -1],
    "south": [0, 0, 1],
    "west": [-1, 0, 0],
    "east": [1, 0, 0],
}


def rotate(vector: list[float], axis: str, angle: float, origin: list[float]) -> list[float]:
    x, y, z = [v - o for v, o in zip(vector, origin, strict=True)]
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    if axis == "x":
        values = [x, y * c - z * s, y * s + z * c]
    elif axis == "y":
        values = [x * c + z * s, y, -x * s + z * c]
    else:
        values = [x * c - y * s, x * s + y * c, z]
    return [v + o for v, o in zip(values, origin, strict=True)]


def quads(low: list[float], high: list[float]) -> dict[str, list[list[float]]]:
    x0, y0, z0 = low
    x1, y1, z1 = high
    return {
        "up": [[x0, y1, z1], [x1, y1, z1], [x1, y1, z0], [x0, y1, z0]],
        "down": [[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]],
        "north": [[x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0]],
        "south": [[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]],
        "west": [[x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0]],
        "east": [[x1, y0, z1], [x1, y0, z0], [x1, y1, z0], [x1, y1, z1]],
    }


def default_uv(low: list[float], high: list[float], direction: str) -> list[float]:
    x0, y0, z0 = low
    x1, y1, z1 = high
    return {
        "up": [x0, z0, x1, z1],
        "down": [x0, 16 - z1, x1, 16 - z0],
        "north": [16 - x1, 16 - y1, 16 - x0, 16 - y0],
        "south": [x0, 16 - y1, x1, 16 - y0],
        "west": [z0, 16 - y1, z1, 16 - y0],
        "east": [16 - z1, 16 - y1, 16 - z0, 16 - y0],
    }[direction]


def face_uv(
    uv: list[float], width: float = 16, height: float = 16, turns: int = 0
) -> list[list[float]]:
    points = [
        [uv[0] / width, uv[3] / height],
        [uv[2] / width, uv[3] / height],
        [uv[2] / width, uv[1] / height],
        [uv[0] / width, uv[1] / height],
    ]
    # Minecraft clockwise face rotation advances the vertex UV index.
    return points[turns % 4 :] + points[: turns % 4]


def projected_uv(point: list[float], direction: str) -> list[float]:
    x, y, z = point
    return {
        "up": [x, z],
        "down": [x, 16 - z],
        "north": [16 - x, 16 - y],
        "south": [x, 16 - y],
        "west": [z, 16 - y],
        "east": [16 - z, 16 - y],
    }[direction]
