import random
import numpy as np
import heapq
from dataclasses import dataclass, field
import world
import settings
import creature_net
import features

@dataclass
class CreatureState:
    x: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int32))
    y: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int32))
    hp: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int32))
    gold: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int32))
    traits: np.ndarray = field(default_factory=lambda: np.empty((0, creature_net.TRAIT_DIM), dtype=np.float32))
    alive: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.bool_))
    target: list = field(default_factory=list)

creature_state = CreatureState()
NEIGHBOR_DELTAS = ((0, -1), (0, 1), (1, 0), (-1, 0))

def _astar_first_step(sx, sy, gx, gy):
    if world.is_blocked(gx, gy) or (sx == gx and sy == gy):
        return None
    open_heap = []
    heapq.heappush(open_heap, (0, sx, sy))
    came_from = {}
    g_score = {(sx, sy): 0}
    while open_heap:
        _, cx, cy = heapq.heappop(open_heap)
        if cx == gx and cy == gy:
            cur = (cx, cy)
            while came_from.get(cur) != (sx, sy) and cur in came_from:
                cur = came_from[cur]
            return cur
        for dx, dy in NEIGHBOR_DELTAS:
            nx, ny = cx + dx, cy + dy
            if world.is_blocked(nx, ny):
                continue
            tentative_g = g_score[(cx, cy)] + 1
            if tentative_g < g_score.get((nx, ny), float('inf')):
                came_from[(nx, ny)] = (cx, cy)
                g_score[(nx, ny)] = tentative_g
                f = tentative_g + abs(nx - gx) + abs(ny - gy)
                heapq.heappush(open_heap, (f, nx, ny))
    return None

def _gold_index_at(x, y):
    for i in range(settings.GOLD_COUNT):
        if (world.world_state.gold_active[i]
                and int(world.world_state.gold_x[i]) == x
                and int(world.world_state.gold_y[i]) == y):
            return i
    return None

def _creature_at(x, y, exclude):
    for j in range(len(creature_state.x)):
        if j != exclude and creature_state.alive[j] and int(creature_state.x[j]) == x and int(creature_state.y[j]) == y:
            return j
    return None

def select_target(ci):
    traits = creature_state.traits[ci]
    best_score = None
    best_target = None
    for gi in range(settings.GOLD_COUNT):
        if not world.world_state.gold_active[gi]:
            continue
        gx, gy = int(world.world_state.gold_x[gi]), int(world.world_state.gold_y[gi])
        feat = features.build_features(creature_state, ci, gx, gy, "gold")
        s = creature_net.net_forward(traits, feat)
        if best_score is None or s > best_score:
            best_score = s
            best_target = {"type": "gold", "gold_index": gi}
    for j in range(len(creature_state.x)):
        if j == ci or not creature_state.alive[j]:
            continue
        jx, jy = int(creature_state.x[j]), int(creature_state.y[j])
        feat = features.build_features(creature_state, ci, jx, jy, "creature")
        s = creature_net.net_forward(traits, feat)
        if best_score is None or s > best_score:
            best_score = s
            best_target = {"type": "creature", "id": j}
    return best_target

def _target_coords(target):
    if target is None:
        return None, None
    if target["type"] == "gold":
        gi = target["gold_index"]
        if gi < settings.GOLD_COUNT and world.world_state.gold_active[gi]:
            return int(world.world_state.gold_x[gi]), int(world.world_state.gold_y[gi])
    elif target["type"] == "creature":
        j = target["id"]
        if j < len(creature_state.x) and creature_state.alive[j]:
            return int(creature_state.x[j]), int(creature_state.y[j])
    return None, None

def _random_step(x, y):
    deltas = list(NEIGHBOR_DELTAS)
    random.shuffle(deltas)
    for dx, dy in deltas:
        nx, ny = x + dx, y + dy
        if not world.is_blocked(nx, ny):
            return nx, ny
    return x, y

def choose_move(ci):
    x, y = int(creature_state.x[ci]), int(creature_state.y[ci])
    target = select_target(ci)
    creature_state.target[ci] = target
    tx, ty = _target_coords(target)
    if tx is None or (x == tx and y == ty):
        return _random_step(x, y)
    step = _astar_first_step(x, y, tx, ty)
    return step if step is not None else _random_step(x, y)

def _respawn_creature(i, parent):
    cx = random.randint(settings.GRID_COLS // 4, 3 * settings.GRID_COLS // 4)
    cy = random.randint(settings.GRID_ROWS // 4, 3 * settings.GRID_ROWS // 4)
    for _ in range(50):
        if not world.is_blocked(cx, cy):
            break
        cx = random.randint(settings.GRID_COLS // 4, 3 * settings.GRID_COLS // 4)
        cy = random.randint(settings.GRID_ROWS // 4, 3 * settings.GRID_ROWS // 4)
    creature_state.x[i] = cx
    creature_state.y[i] = cy
    creature_state.hp[i] = 100
    creature_state.gold[i] = 0
    creature_state.alive[i] = True
    creature_state.target[i] = None
    creature_state.traits[i] = creature_net.mutate_traits(creature_state.traits[parent].copy(), settings.MUTATION_STD)

def create_creatures(count):
    xs, ys = [], []
    while len(xs) < count:
        x = random.randint(0, settings.GRID_COLS - 1)
        y = random.randint(0, settings.GRID_ROWS - 1)
        if not world.is_blocked(x, y):
            xs.append(x)
            ys.append(y)
    cap = settings.CREATURE_SLOTS
    creature_state.x = np.zeros(cap, dtype=np.int32)
    creature_state.y = np.zeros(cap, dtype=np.int32)
    creature_state.hp = np.zeros(cap, dtype=np.int32)
    creature_state.gold = np.zeros(cap, dtype=np.int32)
    creature_state.traits = np.stack([creature_net.init_traits() for _ in range(cap)]).astype(np.float32)
    creature_state.alive = np.zeros(cap, dtype=np.bool_)
    creature_state.target = [None] * cap
    for i in range(count):
        creature_state.x[i] = xs[i]
        creature_state.y[i] = ys[i]
        creature_state.hp[i] = 100
        creature_state.alive[i] = True
    world.set_creature_count(cap)

def _replace():
    alive_indices = np.where(creature_state.alive)[0]
    if len(alive_indices) < 2:
        return
    parent = int(alive_indices[np.argmax(creature_state.gold[alive_indices])])
    alive_gold = creature_state.gold[alive_indices]
    min_gold = int(np.min(alive_gold))
    culled = np.where(creature_state.alive & (creature_state.gold == min_gold))[0]
    dead = np.where(~creature_state.alive)[0]
    print(f"[cull] parent {parent} gold {int(creature_state.gold[parent])} copied to {len(culled)} gold {min_gold}, {len(dead)} dead")
    for i in culled:
        _respawn_creature(int(i), parent)
    for i in dead:
        _respawn_creature(int(i), parent)
    creature_state.gold[creature_state.alive] = 0

def _interact_gold(i, gi):
    px, py = int(creature_state.x[i]), int(creature_state.y[i])
    world.world_state.gold_active[gi] = False
    creature_state.gold[i] += 1
    creature_state.target[i] = None
    world.spawn_gold(gi)
    if settings.PRINT_PICKUP:
        print(f"[creature {i}] picked up gold at ({px},{py}), total={int(creature_state.gold[i])}")

def _fight_creatures(i, j):
    power_i = float(creature_state.gold[i]) + random.random()
    power_j = float(creature_state.gold[j]) + random.random()
    winner = i if power_i >= power_j else j
    loser = j if winner == i else i
    damage = random.randint(5, 20)
    creature_state.hp[loser] = max(0, int(creature_state.hp[loser]) - damage)
    creature_state.target[i] = None
    creature_state.target[j] = None
    if creature_state.hp[loser] == 0:
        creature_state.alive[loser] = False
        if settings.PRINT_INTERACTIONS: print(f"[fight] creature {loser} killed by {winner}")
    else:
        if settings.PRINT_INTERACTIONS: print(f"[fight] creature {winner} hit {loser} for {damage}, hp={int(creature_state.hp[loser])}")

def _talk_creatures(i, j):
    creature_state.target[i] = None
    creature_state.target[j] = None
    if settings.PRINT_INTERACTIONS: print(f"[talk] creature {i} talked to creature {j}")

def _ignore_creatures(i, j):
    creature_state.target[i] = None
    if settings.PRINT_INTERACTIONS: print(f"[ignore] creature {i} ignored creature {j}")

def _choose_creature_interaction(i, j):
    roll = random.random()
    if roll < 0.5:
        _fight_creatures(i, j)
    elif roll < 0.8:
        _talk_creatures(i, j)
    else:
        _ignore_creatures(i, j)

def _dispatch_interactions(i):
    x, y = int(creature_state.x[i]), int(creature_state.y[i])
    gi = _gold_index_at(x, y)
    if gi is not None:
        _interact_gold(i, gi)
        return
    j = _creature_at(x, y, exclude=i)
    if j is not None:
        _choose_creature_interaction(i, j)

def update_move(i):
    nx, ny = choose_move(i)
    creature_state.x[i] = nx
    creature_state.y[i] = ny
    _dispatch_interactions(i)

def update_creatures():
    for i in range(len(creature_state.x)):
        if creature_state.alive[i]:
            creature_state.hp[i] = min(100, int(creature_state.hp[i]) + settings.HP_REGEN)
            update_move(i)
    world.tick()
    t = int(world.world_state.tick_counter)
    if settings.CULL_INTERVAL > 0 and t % settings.CULL_INTERVAL == 0:
        _replace()
