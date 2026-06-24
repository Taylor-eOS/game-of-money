import numpy as np
import random
import settings
from dataclasses import dataclass, field

@dataclass
class WorldState:
    blocks: set = field(default_factory=set)
    areas: list = field(default_factory=list)
    visit: np.ndarray = field(default_factory=lambda: np.empty((0, 0), dtype=np.int32))
    gold_positions: set = field(default_factory=set)
    gold_respawn_timer: dict = field(default_factory=dict)

world_state = None

def init_world():
    global world_state
    world_state = WorldState()
    if hasattr(settings, "WALLS"):
        for x1, y1, x2, y2 in settings.WALLS:
            for x in range(min(x1, x2), max(x1, x2) + 1):
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    world_state.blocks.add((x, y))
    if hasattr(settings, "AREAS"):
        for x1, y1, x2, y2, name in settings.AREAS:
            world_state.areas.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), name))
    world_state.visit = np.zeros((settings.ROWS, settings.COLS), dtype=np.int32)
    spawn_gold(settings.GOLD_COUNT)

def is_blocked(x, y):
    if x < 0 or y < 0 or x >= settings.COLS or y >= settings.ROWS:
        return True
    return (x, y) in world_state.blocks

def get_area(x, y):
    for x1, y1, x2, y2, name in world_state.areas:
        if x1 <= x <= x2 and y1 <= y <= y2:
            return name
    return None

def spawn_gold(count):
    attempts = 0
    while len(world_state.gold_positions) < count and attempts < count * 20:
        x = random.randint(0, settings.COLS - 1)
        y = random.randint(0, settings.ROWS - 1)
        if not is_blocked(x, y) and (x, y) not in world_state.gold_positions:
            world_state.gold_positions.add((x, y))
        attempts += 1

def tick_gold_respawn():
    to_respawn = []
    for pos, timer in list(world_state.gold_respawn_timer.items()):
        world_state.gold_respawn_timer[pos] = timer - 1
        if world_state.gold_respawn_timer[pos] <= 0:
            to_respawn.append(pos)
    for pos in to_respawn:
        del world_state.gold_respawn_timer[pos]
        if not is_blocked(*pos):
            world_state.gold_positions.add(pos)

def nearest_gold_distance(x, y):
    if not world_state.gold_positions:
        return max(settings.COLS, settings.ROWS)
    return min(abs(gx - x) + abs(gy - y) for gx, gy in world_state.gold_positions)

def count_open_neighbors(x, y):
    NEIGHBOR_DELTAS = ((0, -1), (0, 1), (1, 0), (-1, 0))
    return sum(1 for dx, dy in NEIGHBOR_DELTAS if not is_blocked(x + dx, y + dy))
