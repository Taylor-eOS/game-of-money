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
    tick_counter: int = 0

world_state = WorldState()

def init_world():
    world_state.blocks = set()
    world_state.areas = []
    world_state.gold_positions = set()
    world_state.gold_respawn_timer = {}
    world_state.tick_counter = 0
    if hasattr(settings, "WALLS"):
        for x1, y1, x2, y2 in settings.WALLS:
            for x in range(min(x1, x2), max(x1, x2) + 1):
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    world_state.blocks.add((x, y))
    if hasattr(settings, "AREAS"):
        for x1, y1, x2, y2, name in settings.AREAS:
            world_state.areas.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), name))
    world_state.visit = np.zeros((settings.GRID_ROWS, settings.GRID_COLS), dtype=np.int32)
    spawn_gold(settings.GOLD_COUNT)

def is_blocked(x, y):
    if x < 0 or y < 0 or x >= settings.GRID_COLS or y >= settings.GRID_ROWS:
        return True
    return (x, y) in world_state.blocks

def spawn_gold(count):
    attempts = 0
    while len(world_state.gold_positions) < count and attempts < count * 20:
        x = random.randint(0, settings.GRID_COLS - 1)
        y = random.randint(0, settings.GRID_ROWS - 1)
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

