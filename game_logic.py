import random
import numpy as np
import settings

creature_x    = np.empty(0, dtype=np.int32)
creature_y    = np.empty(0, dtype=np.int32)
creature_hp   = np.empty(0, dtype=np.int32)
creature_gold = np.empty(0, dtype=np.int32)
world_blocks  = set()

def init_world():
    global world_blocks
    world_blocks = set()
    if hasattr(settings, "WALLS"):
        for x1, y1, x2, y2 in settings.WALLS:
            for x in range(min(x1, x2), max(x1, x2) + 1):
                for y in range(min(y1, y2), max(y1, y2) + 1):
                    world_blocks.add((x, y))

def is_blocked(x, y):
    if x < 0 or y < 0 or x >= settings.COLS or y >= settings.ROWS:
        return True
    return (x, y) in world_blocks

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

def update_creatures():
    global creature_x, creature_y
    count = len(creature_x)
    dx = np.random.randint(-1, 2, size=count, dtype=np.int32)
    dy = np.random.randint(-1, 2, size=count, dtype=np.int32)
    nx = creature_x + dx
    ny = creature_y + dy
    for i in range(count):
        if not is_blocked(nx[i], ny[i]):
            creature_x[i] = nx[i]
            creature_y[i] = ny[i]
