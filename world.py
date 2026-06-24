import numpy as np
import random
import settings

world_blocks = set()
world_areas = []
world_visit = np.empty((0, 0), dtype=np.int32)
gold_positions = set()
gold_respawn_timer = {}

def init_world():
    global world_blocks, world_areas, world_visit
    world_blocks = set()
    if hasattr(settings, "WALLS"):
        for x1, y1, x2, y2 in settings.WALLS:
            for x in range(min(x1, x2), max(x1, x2) + 1):
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    world_blocks.add((x, y))
    world_areas = []
    if hasattr(settings, "AREAS"):
        for x1, y1, x2, y2, name in settings.AREAS:
            world_areas.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), name))
    world_visit = np.zeros((settings.ROWS, settings.COLS), dtype=np.int32)
    spawn_gold(settings.GOLD_COUNT)

def is_blocked(x, y):
    if x < 0 or y < 0 or x >= settings.COLS or y >= settings.ROWS:
        return True
    return (x, y) in world_blocks

def get_area(x, y):
    for x1, y1, x2, y2, name in world_areas:
        if x1 <= x <= x2 and y1 <= y <= y2:
            return name
    return None

def spawn_gold(count):
    attempts = 0
    while len(gold_positions) < count and attempts < count * 20:
        x = random.randint(0, settings.COLS - 1)
        y = random.randint(0, settings.ROWS - 1)
        if not is_blocked(x, y) and (x, y) not in gold_positions:
            gold_positions.add((x, y))
        attempts += 1

def tick_gold_respawn():
    to_respawn = []
    for pos, timer in list(gold_respawn_timer.items()):
        gold_respawn_timer[pos] = timer - 1
        if gold_respawn_timer[pos] <= 0:
            to_respawn.append(pos)
    for pos in to_respawn:
        del gold_respawn_timer[pos]
        if not is_blocked(*pos):
            gold_positions.add(pos)

def nearest_gold_distance(x, y):
    if not gold_positions:
        return max(settings.COLS, settings.ROWS)
    return min(abs(gx - x) + abs(gy - y) for gx, gy in gold_positions)

def count_open_neighbors(x, y):
    NEIGHBOR_DELTAS = ((0, -1), (0, 1), (1, 0), (-1, 0))
    return sum(1 for dx, dy in NEIGHBOR_DELTAS if not is_blocked(x + dx, y + dy))
