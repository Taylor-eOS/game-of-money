import heapq
import numpy as np
import random
import settings
import world
from gguf_llm_library import ask_llm

creature_x = np.empty(0, dtype=np.int32)
creature_y = np.empty(0, dtype=np.int32)
creature_hp = np.empty(0, dtype=np.int32)
creature_gold = np.empty(0, dtype=np.int32)
creature_age = np.empty(0, dtype=np.int32)
creature_status = np.empty(0, dtype=np.float32)
creature_traits = np.empty((0, 6), dtype=np.float32)
creature_score = np.empty(0, dtype=np.float32)
creature_alive = np.empty(0, dtype=np.bool_)
creature_last_action = []
creature_last_interaction = []
creature_shirt = []
creature_target = []
creature_path = []

TRAIT_NAMES = ("wealth_drive", "status_drive", "social_distance", "curiosity", "caution", "aggression")
DIRECTIONS = ("north", "south", "east", "west")
DIRECTION_DELTAS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
NEIGHBOR_DELTAS = ((0, -1), (0, 1), (1, 0), (-1, 0))
_tick_counter = 0

def init_world():
    world.init_world()

def local_status_field(x, y):
    total = 0.0
    for j in range(len(creature_x)):
        if not creature_alive[j]:
            continue
        ox, oy = int(creature_x[j]), int(creature_y[j])
        dist = abs(ox - x) + abs(oy - y)
        if 0 < dist <= settings.STATUS_RADIUS:
            total += float(creature_status[j]) / dist
    return total

def nearby_creatures(i, x, y):
    others = []
    for j in range(len(creature_x)):
        if j == i or not creature_alive[j]:
            continue
        ox, oy = int(creature_x[j]), int(creature_y[j])
        dist = abs(ox - x) + abs(oy - y)
        others.append((dist, j, ox, oy))
    others.sort(key=lambda item: item[0])
    return others

def spawn_creatures(count):
    global creature_x, creature_y, creature_hp, creature_gold, creature_age
    global creature_status, creature_traits, creature_last_action
    global creature_last_interaction, creature_score, creature_shirt, creature_alive
    global creature_target, creature_path
    xs, ys = [], []
    while len(xs) < count:
        x = random.randint(0, settings.COLS - 1)
        y = random.randint(0, settings.ROWS - 1)
        if not world.is_blocked(x, y):
            xs.append(x)
            ys.append(y)
    creature_x = np.array(xs, dtype=np.int32)
    creature_y = np.array(ys, dtype=np.int32)
    creature_hp = np.full(count, 100, dtype=np.int32)
    creature_gold = np.zeros(count, dtype=np.int32)
    creature_age = np.zeros(count, dtype=np.int32)
    creature_status = np.zeros(count, dtype=np.float32)
    creature_traits = np.random.uniform(0.25, 0.75, size=(count, len(TRAIT_NAMES))).astype(np.float32)
    creature_last_action = [""] * count
    creature_last_interaction = [""] * count
    creature_score = np.zeros(count, dtype=np.float32)
    creature_alive = np.ones(count, dtype=np.bool_)
    creature_shirt = [
        (random.randint(80, 220), random.randint(80, 220), random.randint(80, 220))
        for _ in range(count)
    ]
    creature_target = [None] * count
    creature_path = [[] for _ in range(count)]

def astar(sx, sy, gx, gy):
    if world.is_blocked(gx, gy):
        return []
    if sx == gx and sy == gy:
        return []
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
            path = []
            cur = (cx, cy)
            while cur in came_from:
                path.append(cur)
                cur = came_from[cur]
            path.reverse()
            return path
        for dx, dy in NEIGHBOR_DELTAS:
            nx, ny = cx + dx, cy + dy
            if world.is_blocked(nx, ny):
                continue
            tentative_g = g_score[(cx, cy)] + 1
            if tentative_g < g_score.get((nx, ny), float("inf")):
                came_from[(nx, ny)] = (cx, cy)
                g_score[(nx, ny)] = tentative_g
                f = tentative_g + abs(nx - gx) + abs(ny - gy)
                heapq.heappush(open_heap, (f, nx, ny))
    return []

def _random_open_cell():
    for _ in range(200):
        x = random.randint(0, settings.COLS - 1)
        y = random.randint(0, settings.ROWS - 1)
        if not world.is_blocked(x, y):
            return x, y
    return None, None

def select_target(i):
    x, y = int(creature_x[i]), int(creature_y[i])
    if world.gold_positions:
        gx, gy = min(world.gold_positions, key=lambda p: abs(p[0] - x) + abs(p[1] - y))
        return {"type": "gold", "pos": (gx, gy)}
    wx, wy = _random_open_cell()
    if wx is not None:
        return {"type": "wander", "pos": (wx, wy)}
    return None

def _target_position(i, target):
    if target is None:
        return None, None
    if target["type"] in ("gold", "wander"):
        return target["pos"]
    if target["type"] == "creature":
        j = target["id"]
        if j < len(creature_x) and creature_alive[j]:
            return int(creature_x[j]), int(creature_y[j])
    return None, None

def _target_still_valid(i, target):
    if target is None:
        return False
    if target["type"] == "gold":
        return target["pos"] in world.gold_positions
    if target["type"] == "wander":
        return True
    if target["type"] == "creature":
        j = target["id"]
        return j < len(creature_x) and creature_alive[j]
    return False

def _path_still_valid(i):
    path = creature_path[i]
    if not path:
        return False
    nx, ny = path[0]
    return not world.is_blocked(nx, ny)

def choose_move(i):
    x, y = int(creature_x[i]), int(creature_y[i])
    target = creature_target[i]
    if not _target_still_valid(i, target):
        target = select_target(i)
        creature_target[i] = target
        creature_path[i] = []
    if target is None:
        return x, y
    tx, ty = _target_position(i, target)
    if tx is None:
        creature_target[i] = None
        creature_path[i] = []
        return x, y
    if x == tx and y == ty:
        creature_target[i] = None
        creature_path[i] = []
        return x, y
    if target["type"] == "creature":
        creature_path[i] = []
    if not _path_still_valid(i):
        creature_path[i] = astar(x, y, tx, ty)
    if creature_path[i]:
        nx, ny = creature_path[i].pop(0)
        return nx, ny
    for dx, dy in random.sample(list(NEIGHBOR_DELTAS), len(NEIGHBOR_DELTAS)):
        nx, ny = x + dx, y + dy
        if not world.is_blocked(nx, ny):
            return nx, ny
    return x, y

def _effect_talk(i, j):
    aggression_i = float(creature_traits[i, 5])
    social_i = 1.0 - float(creature_traits[i, 2])
    friendly = random.random() < (social_i * (1.0 - aggression_i))
    if friendly:
        creature_status[i] = np.clip(creature_status[i] + 0.1, 0.0, 10.0)
        creature_score[i] += 0.2
    return "friendly" if friendly else "hostile"

def _effect_trade(i, j):
    if int(creature_gold[i]) <= 0:
        return "failure"
    wealth_drive_j = float(creature_traits[j, 0])
    success = random.random() < wealth_drive_j
    if success:
        creature_gold[i] -= 1
        creature_gold[j] += 1
        creature_status[i] = np.clip(creature_status[i] + 0.2, 0.0, 10.0)
        creature_score[i] += 0.5
    return "success" if success else "failure"

def _effect_fight(i, j):
    power_i = float(creature_status[i]) + float(creature_traits[i, 5]) + random.random()
    power_j = float(creature_status[j]) + float(creature_traits[j, 5]) + random.random()
    winner = i if power_i >= power_j else j
    loser = j if winner == i else i
    creature_hp[loser] = max(0, int(creature_hp[loser]) - random.randint(5, 20))
    if creature_hp[loser] == 0:
        creature_alive[loser] = False
    creature_status[winner] = np.clip(creature_status[winner] + 0.4, 0.0, 10.0)
    creature_status[loser] = np.clip(creature_status[loser] - 0.2, 0.0, 10.0)
    creature_score[winner] += 1.0
    return f"winner={winner}"

INTERACTION_TYPES = {
    "talk":  {"description": "exchange words, friendly or hostile", "effect": _effect_talk},
    "trade": {"description": "attempt to exchange gold for goodwill", "effect": _effect_trade},
    "fight": {"description": "physical contest for dominance",       "effect": _effect_fight},
}

def build_interaction_prompt(i, j, interaction_type, outcome):
    desc = INTERACTION_TYPES[interaction_type]["description"]
    prompt = (
        f"Two creatures meet and {desc} in a grid world simulation. "
        f"Creature {i}: hp={int(creature_hp[i])}, gold={int(creature_gold[i])}, "
        f"status={float(creature_status[i]):.2f}, "
        f"aggression={float(creature_traits[i, 5]):.2f}, "
        f"caution={float(creature_traits[i, 4]):.2f}. "
        f"Creature {j}: hp={int(creature_hp[j])}, gold={int(creature_gold[j])}, "
        f"status={float(creature_status[j]):.2f}, "
        f"aggression={float(creature_traits[j, 5]):.2f}. "
        f"The outcome was: {outcome}. "
        f"Describe what happened in one short vivid sentence."
    )
    return prompt

def handle_proximity_events(i):
    x, y = int(creature_x[i]), int(creature_y[i])
    others = nearby_creatures(i, x, y)
    if not others:
        return
    nearest_dist, j, ox, oy = others[0]
    if nearest_dist > 1:
        return
    if random.random() > settings.INTERACTION_CHANCE:
        return
    aggression = float(creature_traits[i, 5])
    status_drive = float(creature_traits[i, 1])
    if aggression > 0.6:
        interaction_type = "fight"
    elif status_drive > 0.5 and int(creature_gold[i]) > 0:
        interaction_type = "trade"
    else:
        interaction_type = "talk"
    creature_last_interaction[i] = interaction_type
    outcome = INTERACTION_TYPES[interaction_type]["effect"](i, j)
    if settings.ENABLE_LLM_INTERACTIONS:
        prompt = build_interaction_prompt(i, j, interaction_type, outcome)
        print(f"[interaction {i},{j}] type={interaction_type} prompt: {prompt}")
        flavor = ask_llm(prompt, settings.LLM_MODEL).strip()
        print(f"[interaction {i},{j}] flavor: {flavor}")
    else:
        print(f"[interaction {i},{j}] type={interaction_type} outcome: {outcome}")

def check_gold_pickup(i):
    pos = (int(creature_x[i]), int(creature_y[i]))
    if pos in world.gold_positions:
        world.gold_positions.discard(pos)
        creature_gold[i] += 1
        creature_status[i] = np.clip(creature_status[i] + 1.0, 0.0, 10.0)
        world.gold_respawn_timer[pos] = world.GOLD_RESPAWN_TICKS
        creature_score[i] += 2.0
        if creature_target[i] is not None and creature_target[i].get("pos") == pos:
            creature_target[i] = None
            creature_path[i] = []
        print(f"[creature {i}] picked up gold at {pos}, total={int(creature_gold[i])}")

def accumulate_survival_score(i):
    creature_score[i] += (int(creature_hp[i]) / 100.0) * 0.1 + int(creature_gold[i]) * 0.05
    creature_status[i] = np.clip(creature_status[i] + 0.01, 0.0, 10.0)

def tick_status_decay():
    global creature_status
    creature_status = np.clip(creature_status - settings.STATUS_DECAY, 0.0, 10.0)

def apply_personality_feedback(i, moved, nx, ny):
    pass

def apply_generational_nudge():
    alive_indices = [i for i in range(len(creature_x)) if creature_alive[i]]
    if len(alive_indices) < 2:
        return
    best_i = alive_indices[int(np.argmax(creature_score[alive_indices]))]
    best_traits = creature_traits[best_i].copy()
    nudge = settings.GENERATION_NUDGE_RATE
    for i in alive_indices:
        if i == best_i:
            continue
        creature_traits[i] = np.clip(
            creature_traits[i] * (1.0 - nudge) + best_traits * nudge,
            0.0, 1.0
        )
    creature_score[:] = 0.0
    print(f"[generation] nudged toward creature {best_i}: {best_traits.tolist()}")

def update_creature_move(i):
    x, y = int(creature_x[i]), int(creature_y[i])
    nx, ny = choose_move(i)
    moved = (nx != x or ny != y)
    if moved:
        creature_x[i] = nx
        creature_y[i] = ny
        world.world_visit[ny, nx] += 1
    creature_last_action[i] = f"({nx},{ny})"
    creature_age[i] += 1
    check_gold_pickup(i)
    accumulate_survival_score(i)
    apply_personality_feedback(i, moved, nx, ny)

def update_creature_interact(i):
    handle_proximity_events(i)

def update_creatures():
    global _tick_counter
    world.tick_gold_respawn()
    tick_status_decay()
    for i in range(len(creature_x)):
        if creature_alive[i]:
            update_creature_move(i)
    for i in range(len(creature_x)):
        if creature_alive[i]:
            update_creature_interact(i)
    _tick_counter += 1
    if _tick_counter % settings.GENERATION_TICKS == 0:
        apply_generational_nudge()
