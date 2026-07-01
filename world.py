import numpy as np
import random
import settings
from dataclasses import dataclass, field

@dataclass
class WorldState:
    blocks: set = field(default_factory=set)
    areas: list = field(default_factory=list)
    gold_x: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int32))
    gold_y: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int32))
    gold_active: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.bool_))
    active_targets: list = field(default_factory=list)
    creature_count: int = 0
    tick_counter: int = 0

world_state = WorldState()

def init_world():
    world_state.blocks = set(settings.WALL_CELLS)
    world_state.areas = []
    world_state.tick_counter = 0
    world_state.active_targets = []
    world_state.creature_count = 0
    for x1, y1, x2, y2, name in settings.AREAS:
        world_state.areas.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), name))
    world_state.gold_x = np.zeros(settings.GOLD_COUNT, dtype=np.int32)
    world_state.gold_y = np.zeros(settings.GOLD_COUNT, dtype=np.int32)
    world_state.gold_active = np.zeros(settings.GOLD_COUNT, dtype=np.bool_)

def set_creature_count(count):
    world_state.creature_count = count
    world_state.active_targets = list(range(count))
    for i in range(settings.GOLD_COUNT):
        spawn_gold(i)

def is_blocked(x, y):
    if x < 0 or y < 0 or x >= settings.GRID_COLS or y >= settings.GRID_ROWS:
        return True
    return (x, y) in world_state.blocks

def spawn_gold(gold_index):
    attempts = 0
    while attempts < 100:
        x = random.randint(0, settings.GRID_COLS - 1)
        y = random.randint(0, settings.GRID_ROWS - 1)
        if not is_blocked(x, y):
            world_state.gold_x[gold_index] = x
            world_state.gold_y[gold_index] = y
            world_state.gold_active[gold_index] = True
            target_id = world_state.creature_count + gold_index
            if target_id not in world_state.active_targets:
                world_state.active_targets.append(target_id)
            return
        attempts += 1

def gold_target_id(gold_index):
    return world_state.creature_count + gold_index

def remove_target(target_id):
    if target_id in world_state.active_targets:
        world_state.active_targets.remove(target_id)

def get_gold_positions():
    return [(int(world_state.gold_x[i]), int(world_state.gold_y[i])) for i in range(settings.GOLD_COUNT) if world_state.gold_active[i]]

def tick():
    world_state.tick_counter += 1
