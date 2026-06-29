import random
import numpy as np
import heapq
from dataclasses import dataclass, field
import world
import settings
import creature_net

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

def _candidate_features(ci, tx, ty, is_gold_flag):
    cx, cy = int(creature_state.x[ci]), int(creature_state.y[ci])
    manhattan = abs(tx - cx) + abs(ty - cy)
    dx = float(tx - cx) / max(settings.GRID_COLS, settings.GRID_ROWS)
    dy = float(ty - cy) / max(settings.GRID_COLS, settings.GRID_ROWS)
    dist = np.log1p(float(manhattan)) / np.log1p(settings.GRID_COLS + settings.GRID_ROWS)
    r = settings.DENSITY_RADIUS
    alive_mask = creature_state.alive
    alive_x = creature_state.x[alive_mask]
    alive_y = creature_state.y[alive_mask]
    density = float(np.sum((np.abs(alive_x - tx) + np.abs(alive_y - ty)) <= r)) / settings.DENSITY_NORM
    closer_count = float(np.sum((np.abs(alive_x - tx) + np.abs(alive_y - ty)) < manhattan)) / max(1.0, float(np.sum(alive_mask)))
    hp_norm = float(creature_state.hp[ci]) / 100.0
    own_gold = float(creature_state.gold[ci])
    own_gold_norm = np.log1p(own_gold) / np.log1p(50.0)
    alive_indices = np.where(alive_mask)[0]
    gold_vals = creature_state.gold[alive_indices].astype(np.float32)
    rank_norm = float(np.sum(gold_vals < own_gold)) / max(1.0, float(len(alive_indices) - 1))
    own_x_norm = float(cx) / max(1, settings.GRID_COLS - 1)
    own_y_norm = float(cy) / max(1, settings.GRID_ROWS - 1)
    return np.array([dx, dy, dist, density, closer_count, hp_norm, is_gold_flag, own_gold_norm, rank_norm, 1.0, own_x_norm, own_y_norm], dtype=np.float32)

def _astar_first_step(sx, sy, gx, gy, extra_blocked=None):
    if world.is_blocked(gx, gy):
        return None
    if sx == gx and sy == gy:
        return None
    blocked = extra_blocked or set()
    open_heap = []
    heapq.heappush(open_heap, (0, sx, sy))
    came_from = {}
    g_score = {(sx, sy): 0}
    nodes_expanded = 0
    while open_heap:
        if nodes_expanded >= settings.ASTAR_MAX_NODES:
            break
        _, cx, cy = heapq.heappop(open_heap)
        nodes_expanded += 1
        if cx == gx and cy == gy:
            cur = (cx, cy)
            while came_from.get(cur) != (sx, sy) and cur in came_from:
                cur = came_from[cur]
            return cur
        for dx, dy in NEIGHBOR_DELTAS:
            nx, ny = cx + dx, cy + dy
            if world.is_blocked(nx, ny) or (nx, ny) in blocked:
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

def select_target(ci):
    traits = creature_state.traits[ci]
    best_score = None
    best_target = None
    for gi in range(settings.GOLD_COUNT):
        if not world.world_state.gold_active[gi]:
            continue
        gx, gy = int(world.world_state.gold_x[gi]), int(world.world_state.gold_y[gi])
        features = _candidate_features(ci, gx, gy, 1.0)
        s = creature_net.net_forward(traits, features)
        if best_score is None or s > best_score:
            best_score = s
            best_target = {"type": "gold", "gold_index": gi, "pos": (gx, gy)}
    for j in range(len(creature_state.x)):
        if j == ci or not creature_state.alive[j]:
            continue
        jx, jy = int(creature_state.x[j]), int(creature_state.y[j])
        features = _candidate_features(ci, jx, jy, 0.0)
        s = creature_net.net_forward(traits, features)
        if best_score is None or s > best_score:
            best_score = s
            best_target = {"type": "creature", "id": j}
    return best_target

def _target_position(ci, target):
    if target is None:
        return None, None
    if target["type"] == "gold":
        gi = target["gold_index"]
        if world.world_state.gold_active[gi]:
            return int(world.world_state.gold_x[gi]), int(world.world_state.gold_y[gi])
        return None, None
    if target["type"] == "creature":
        j = target["id"]
        if j < len(creature_state.x) and creature_state.alive[j]:
            return int(creature_state.x[j]), int(creature_state.y[j])
    return None, None

def _target_still_valid(ci, target):
    if target is None:
        return False
    if target["type"] == "gold":
        gi = target["gold_index"]
        return gi < settings.GOLD_COUNT and world.world_state.gold_active[gi]
    if target["type"] == "creature":
        j = target["id"]
        if not (j < len(creature_state.x) and creature_state.alive[j]):
            return False
        dist = abs(int(creature_state.x[j]) - int(creature_state.x[ci])) + abs(int(creature_state.y[j]) - int(creature_state.y[ci]))
        return dist <= 10
    return False

def choose_move(ci):
    x, y = int(creature_state.x[ci]), int(creature_state.y[ci])
    target = select_target(ci)
    creature_state.target[ci] = target
    if target is None:
        return x, y
    tx, ty = _target_position(ci, target)
    if tx is None:
        creature_state.target[ci] = None
        return x, y
    if x == tx and y == ty:
        return x, y
    occupied = set(zip(creature_state.x[creature_state.alive].tolist(),
                       creature_state.y[creature_state.alive].tolist()))
    occupied.discard((x, y))
    occupied.discard((tx, ty))
    step = _astar_first_step(x, y, tx, ty, extra_blocked=occupied)
    if step is not None:
        return step
    for dx, dy in random.sample(list(NEIGHBOR_DELTAS), len(NEIGHBOR_DELTAS)):
        nx, ny = x + dx, y + dy
        if not world.is_blocked(nx, ny) and (nx, ny) not in occupied:
            return nx, ny
    return x, y

def _respawn_creature(i):
    alive_indices = [j for j in range(len(creature_state.x)) if creature_state.alive[j]]
    if not alive_indices:
        return
    parent = alive_indices[int(np.argmax(creature_state.gold[alive_indices]))]
    cx, cy = random.randint(settings.GRID_COLS // 4, 3 * settings.GRID_COLS // 4), random.randint(settings.GRID_ROWS // 4, 3 * settings.GRID_ROWS // 4)
    for _ in range(50):
        if not world.is_blocked(cx, cy):
            break
        cx, cy = random.randint(settings.GRID_COLS // 4, 3 * settings.GRID_COLS // 4), random.randint(settings.GRID_ROWS // 4, 3 * settings.GRID_ROWS // 4)
    creature_state.x[i] = cx
    creature_state.y[i] = cy
    creature_state.hp[i] = 100
    creature_state.gold[i] = 0
    creature_state.alive[i] = True
    creature_state.target[i] = None
    creature_state.traits[i] = creature_net.mutate_traits(creature_state.traits[parent].copy(), settings.MUTATION_STD)
    print(f"[respawn] creature {i} mutated from {parent}")

def create_creatures(count):
    xs, ys = [], []
    while len(xs) < count:
        x = random.randint(0, settings.GRID_COLS - 1)
        y = random.randint(0, settings.GRID_ROWS - 1)
        if not world.is_blocked(x, y):
            xs.append(x)
            ys.append(y)
    cap = settings.CREATURE_COUNT
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

def _cull_one():
    alive_indices = np.where(creature_state.alive)[0]
    if len(alive_indices) < 2:
        return
    golds = creature_state.gold[alive_indices]
    top_gold = int(np.max(golds))
    base = settings.CULL_GOLD_PERCENTILE * 100
    extra = min(top_gold * settings.CULL_PER_GOLD, settings.CULL_MAX_PERCENTILE * 100 - base)
    threshold_pct = base + extra
    threshold = np.percentile(golds, threshold_pct)
    eligible = alive_indices[golds <= threshold]
    if len(eligible) == 0:
        return
    victim = int(np.random.choice(eligible))
    creature_state.alive[victim] = False
    creature_state.hp[victim] = 0
    print(f"[cull] creature {victim} culled (gold={int(creature_state.gold[victim])}, pct={threshold_pct:.1f})")
    creature_state.gold[creature_state.alive] = 0
    _respawn_creature(victim)

def _breed_one():
    dead_indices = np.where(~creature_state.alive)[0]
    if len(dead_indices) == 0:
        return
    _respawn_creature(int(dead_indices[0]))

def _effect_fight(i, j):
    power_i = float(creature_state.traits[i, 0]) + random.random()
    power_j = float(creature_state.traits[j, 0]) + random.random()
    winner = i if power_i >= power_j else j
    loser = j if winner == i else i
    damage = random.randint(5, 20)
    creature_state.hp[loser] = max(0, int(creature_state.hp[loser]) - damage)
    creature_state.target[i] = None
    creature_state.target[j] = None
    if creature_state.hp[loser] == 0:
        creature_state.alive[loser] = False
        print(f"[fight] creature {loser} killed by {winner}")
        _respawn_creature(loser)
    else:
        print(f"[fight] creature {winner} hit {loser} for {damage}, hp={int(creature_state.hp[loser])}")

def trigger_creature_interaction(i, j):
    if random.random() < settings.INTERACTION_CHANCE:
        return
    _effect_fight(i, j)

def check_gold_pickup(i):
    px, py = int(creature_state.x[i]), int(creature_state.y[i])
    gi = _gold_index_at(px, py)
    if gi is None:
        return
    world.world_state.gold_active[gi] = False
    world.remove_target(world.gold_target_id(gi))
    creature_state.gold[i] += 1
    world.spawn_gold(gi)
    t = creature_state.target[i]
    if t is not None and t.get("type") == "gold" and t.get("gold_index") == gi:
        creature_state.target[i] = None
    if settings.PRINT_PICKUP: print(f"[creature {i}] picked up gold at ({px},{py}), total={int(creature_state.gold[i])}")

def update_creature_move(i):
    x, y = int(creature_state.x[i]), int(creature_state.y[i])
    nx, ny = choose_move(i)
    if nx == x and ny == y:
        return
    target_creature_id = None
    for j in range(len(creature_state.x)):
        if i != j and creature_state.alive[j] and int(creature_state.x[j]) == nx and int(creature_state.y[j]) == ny:
            target_creature_id = j
            break
    if target_creature_id is None:
        creature_state.x[i] = nx
        creature_state.y[i] = ny
        world.world_state.visit[ny, nx] += 1
        check_gold_pickup(i)
    else:
        trigger_creature_interaction(i, target_creature_id)

def update_creatures():
    for i in range(len(creature_state.x)):
        if creature_state.alive[i]:
            creature_state.hp[i] = min(100, int(creature_state.hp[i]) + settings.HP_REGEN)
            update_creature_move(i)
    world.tick()
    t = int(world.world_state.tick_counter)
    if settings.CULL_INTERVAL > 0 and t % settings.CULL_INTERVAL == 0:
        _cull_one()
    if settings.BREED_INTERVAL > 0 and t % settings.BREED_INTERVAL == 0:
        alive_count = int(np.sum(creature_state.alive))
        if alive_count < settings.CREATURE_COUNT:
            _breed_one()
