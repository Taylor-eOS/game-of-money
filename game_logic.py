import random
import numpy as np
import settings

creature_x    = np.empty(0, dtype=np.int32)
creature_y    = np.empty(0, dtype=np.int32)
creature_hp   = np.empty(0, dtype=np.int32)
creature_gold = np.empty(0, dtype=np.int32)
world_blocks  = set()
world_areas   = []

def init_world():
    global world_blocks, world_areas
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

def is_blocked(x, y):
    if x < 0 or y < 0 or x >= settings.COLS or y >= settings.ROWS:
        return True
    return (x, y) in world_blocks

def get_area(x, y):
    for x1, y1, x2, y2, name in world_areas:
        if x1 <= x <= x2 and y1 <= y <= y2:
            return name
    return None

def spawn_creatures(count):
    global creature_x, creature_y, creature_hp, creature_gold
    xs, ys = [], []
    while len(xs) < count:
        x = random.randint(0, settings.COLS - 1)
        y = random.randint(0, settings.ROWS - 1)
        if not is_blocked(x, y):
            xs.append(x)
            ys.append(y)
    creature_x    = np.array(xs, dtype=np.int32)
    creature_y    = np.array(ys, dtype=np.int32)
    creature_hp   = np.full(count, 100, dtype=np.int32)
    creature_gold = np.zeros(count, dtype=np.int32)

def get_creature_state(i):
    print(get_area(int(creature_x[i]), int(creature_y[i])))
    return {
        "index": i,
        "x": int(creature_x[i]),
        "y": int(creature_y[i]),
        "hp": int(creature_hp[i]),
        "gold": int(creature_gold[i]),
        "area": get_area(int(creature_x[i]), int(creature_y[i])),
    }

def decide_move(i):
    dx = random.randint(-1, 1)
    dy = random.randint(-1, 1)
    return dx, dy

def update_creature(i):
    dx, dy = decide_move(i)
    nx = int(creature_x[i]) + dx
    ny = int(creature_y[i]) + dy
    if not is_blocked(nx, ny):
        creature_x[i] = nx
        creature_y[i] = ny

def update_creatures():
    for i in range(len(creature_x)):
        update_creature(i)
