import random
import numpy as np
import heapq
from dataclasses import dataclass, field
from gguf_llm_library import ask_llm
import world
import settings

@dataclass
class CreatureState:
    x: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int32))
    y: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int32))
    hp: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int32))
    gold: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int32))
    traits: np.ndarray = field(default_factory=lambda: np.empty((0, settings.LATENT_DIM), dtype=np.float32))
    score: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.float32))
    alive: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.bool_))
    last_action: list = field(default_factory=list)
    last_interaction: list = field(default_factory=list)
    target: list = field(default_factory=list)

creature_state = CreatureState()

NEIGHBOR_DELTAS = ((0, -1), (0, 1), (1, 0), (-1, 0))

def create_creatures(count):
    xs, ys = [], []
    while len(xs) < count:
        x = random.randint(0, settings.GRID_COLS - 1)
        y = random.randint(0, settings.GRID_ROWS - 1)
        if not world.is_blocked(x, y):
            xs.append(x)
            ys.append(y)
    creature_state.x = np.array(xs, dtype=np.int32)
    creature_state.y = np.array(ys, dtype=np.int32)
    creature_state.hp = np.full(count, 100, dtype=np.int32)
    creature_state.gold = np.zeros(count, dtype=np.int32)
    creature_state.traits = np.random.uniform(0.0, 1.0, size=(count, settings.LATENT_DIM)).astype(np.float32)
    creature_state.last_action = [""] * count
    creature_state.last_interaction = [""] * count
    creature_state.score = np.zeros(count, dtype=np.float32)
    creature_state.alive = np.ones(count, dtype=np.bool_)
    creature_state.target = [None] * count
    world.set_creature_count(count)

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

def select_target(i):
    x, y = int(creature_state.x[i]), int(creature_state.y[i])
    active_gold = []
    for gi in range(settings.GOLD_COUNT):
        if not world.world_state.gold_active[gi]:
            continue
        gx, gy = int(world.world_state.gold_x[gi]), int(world.world_state.gold_y[gi])
        active_gold.append((gi, gx, gy))
    if active_gold:
        if len(active_gold) <= 3:
            gi, gx, gy = random.choice(active_gold)
            return {"type": "gold", "gold_index": gi, "pos": (gx, gy)}
        sample_size = min(5, len(active_gold))
        sampled = random.sample(active_gold, sample_size)
        best_gi, best_gx, best_gy = min(sampled, key=lambda g: abs(g[1] - x) + abs(g[2] - y))
        return {"type": "gold", "gold_index": best_gi, "pos": (best_gx, best_gy)}
    creature_candidates = []
    for j in range(len(creature_state.x)):
        if i == j or not creature_state.alive[j]:
            continue
        cx, cy = int(creature_state.x[j]), int(creature_state.y[j])
        dist = abs(cx - x) + abs(cy - y)
        if dist <= 5:
            creature_candidates.append((j, dist))
    if creature_candidates:
        creature_candidates.sort(key=lambda x: x[1])
        top_candidates = creature_candidates[:min(3, len(creature_candidates))]
        chosen = random.choice(top_candidates)
        return {"type": "creature", "id": chosen[0]}
    return None

def _target_position(i, target):
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

def _target_still_valid(i, target):
    if target is None:
        return False
    if target["type"] == "gold":
        gi = target["gold_index"]
        return gi < settings.GOLD_COUNT and world.world_state.gold_active[gi]
    if target["type"] == "creature":
        j = target["id"]
        return j < len(creature_state.x) and creature_state.alive[j]
    return False

def choose_move(i):
    x, y = int(creature_state.x[i]), int(creature_state.y[i])
    target = creature_state.target[i]
    if not _target_still_valid(i, target):
        target = select_target(i)
        creature_state.target[i] = target
    if target is None:
        return x, y
    tx, ty = _target_position(i, target)
    if tx is None or (x == tx and y == ty):
        creature_state.target[i] = None
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

def _effect_talk(i, j):
    creature_state.score[i] += 0.1
    return "talk"

def _effect_trade(i, j):
    if int(creature_state.gold[i]) <= 0:
        return "failure"
    creature_state.gold[i] -= 1
    creature_state.gold[j] += 1
    creature_state.score[i] += 0.3
    return "success"

def _effect_fight(i, j):
    power_i = float(creature_state.traits[i, 0]) + random.random()
    power_j = float(creature_state.traits[j, 0]) + random.random()
    winner = i if power_i >= power_j else j
    loser = j if winner == i else i
    creature_state.hp[loser] = max(0, int(creature_state.hp[loser]) - random.randint(5, 20))
    if creature_state.hp[loser] == 0:
        creature_state.alive[loser] = False
    creature_state.score[winner] += 0.5
    return f"winner={winner}"

INTERACTION_TYPES = {
    "talk": {"description": "are in proximity", "effect": _effect_talk},
    "trade": {"description": "exchange a resource", "effect": _effect_trade},
    "fight": {"description": "contest physically", "effect": _effect_fight},
}

def build_interaction_prompt(i, j, interaction_type, outcome):
    desc = INTERACTION_TYPES[interaction_type]["description"]
    return f"Two creatures meet in a grid world simulation and {desc}. "

def trigger_creature_interaction(i, j):
    if random.random() < settings.INTERACTION_CHANCE:
        return
    interaction_type = random.choice(list(INTERACTION_TYPES.keys()))
    creature_state.last_interaction[i] = interaction_type
    outcome = INTERACTION_TYPES[interaction_type]["effect"](i, j)
    if settings.ENABLE_LLM_INTERACTIONS:
        prompt = build_interaction_prompt(i, j, interaction_type, outcome)
        print(f"[interaction {i},{j}] type={interaction_type} prompt: {prompt}")
        flavor = ask_llm(prompt, settings.LLM_MODEL).strip()
        print(f"[interaction {i},{j}] flavor: {flavor}")
    else:
        print(f"[interaction {i},{j}] type={interaction_type} outcome: {outcome}")

def check_gold_pickup(i):
    px, py = int(creature_state.x[i]), int(creature_state.y[i])
    gi = _gold_index_at(px, py)
    if gi is None:
        return
    world.world_state.gold_active[gi] = False
    world.remove_target(world.gold_target_id(gi))
    creature_state.gold[i] += 1
    world.respawn_gold_piece(gi)
    creature_state.score[i] += 2.0
    t = creature_state.target[i]
    if t is not None and t.get("type") == "gold" and t.get("gold_index") == gi:
        creature_state.target[i] = None
    print(f"[creature {i}] picked up gold at ({px},{py}), total={int(creature_state.gold[i])}")

def accumulate_survival_score(i):
    creature_state.score[i] += (int(creature_state.hp[i]) / 100.0) * 0.1 + int(creature_state.gold[i]) * 0.05

def apply_generational_nudge():
    alive_indices = [i for i in range(len(creature_state.x)) if creature_state.alive[i]]
    if len(alive_indices) < 2:
        return
    best_i = alive_indices[int(np.argmax(creature_state.score[alive_indices]))]
    best_traits = creature_state.traits[best_i].copy()
    nudge = settings.GENERATION_NUDGE_RATE
    for i in alive_indices:
        if i == best_i:
            continue
        creature_state.traits[i] = np.clip(creature_state.traits[i] * (1.0 - nudge) + best_traits * nudge, 0.0, 1.0)
    creature_state.score[:] = 0.0
    print(f"[generation] nudged toward creature {best_i}: {best_traits.tolist()}")

def update_creature_move(i):
    x, y = int(creature_state.x[i]), int(creature_state.y[i])
    nx, ny = choose_move(i)
    if nx == x and ny == y:
        accumulate_survival_score(i)
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
        creature_state.last_action[i] = f"({nx},{ny})"
        check_gold_pickup(i)
    else:
        trigger_creature_interaction(i, target_creature_id)
        creature_state.last_action[i] = f"interact({target_creature_id})"
    accumulate_survival_score(i)

def update_creatures():
    for i in range(len(creature_state.x)):
        if creature_state.alive[i]:
            update_creature_move(i)
    world.world_state.tick_counter += 1
    if world.world_state.tick_counter % settings.GENERATION_TICKS == 0:
        apply_generational_nudge()
