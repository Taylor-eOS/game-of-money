import numpy as np
import random
import settings
from gguf_llm_library import ask_llm

creature_x = np.empty(0, dtype=np.int32)
creature_y = np.empty(0, dtype=np.int32)
creature_hp = np.empty(0, dtype=np.int32)
creature_gold = np.empty(0, dtype=np.int32)
creature_age = np.empty(0, dtype=np.int32)
creature_status = np.empty(0, dtype=np.float32)
creature_traits = np.empty((0, 6), dtype=np.float32)
creature_last_action = []
creature_last_interaction = []
creature_score = np.empty(0, dtype=np.float32)
world_blocks = set()
world_areas = []
world_visit = np.empty((0, 0), dtype=np.int32)
gold_positions = set()
gold_respawn_timer = {}

TRAIT_NAMES = ("wealth_drive", "status_drive", "social_distance", "curiosity", "caution", "aggression")
DIRECTIONS = ("north", "south", "east", "west")
DIRECTION_DELTAS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
NEIGHBOR_DELTAS = ((0, -1), (0, 1), (1, 0), (-1, 0))

GOLD_COUNT         = getattr(settings, "GOLD_COUNT", 12)
GOLD_RESPAWN_TICKS = getattr(settings, "GOLD_RESPAWN_TICKS", 30)
GENERATION_TICKS   = getattr(settings, "GENERATION_TICKS", 200)
STATUS_DECAY       = getattr(settings, "STATUS_DECAY", 0.005)
STATUS_RADIUS      = getattr(settings, "STATUS_RADIUS", 6)

_tick_counter = 0

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
    spawn_gold(GOLD_COUNT)

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

def local_status_field(x, y):
    total = 0.0
    for j in range(len(creature_x)):
        ox, oy = int(creature_x[j]), int(creature_y[j])
        dist = abs(ox - x) + abs(oy - y)
        if 0 < dist <= STATUS_RADIUS:
            total += float(creature_status[j]) / dist
    return total

def count_open_neighbors(x, y):
    return sum(1 for dx, dy in NEIGHBOR_DELTAS if not is_blocked(x + dx, y + dy))

def nearby_creatures(i, x, y):
    others = []
    for j in range(len(creature_x)):
        if j == i:
            continue
        ox, oy = int(creature_x[j]), int(creature_y[j])
        dist = abs(ox - x) + abs(oy - y)
        others.append((dist, j, ox, oy))
    others.sort(key=lambda item: item[0])
    return others

def spawn_creatures(count):
    global creature_x, creature_y, creature_hp, creature_gold, creature_age
    global creature_status, creature_traits, creature_last_action
    global creature_last_interaction, creature_score
    xs, ys = [], []
    while len(xs) < count:
        x = random.randint(0, settings.COLS - 1)
        y = random.randint(0, settings.ROWS - 1)
        if not is_blocked(x, y):
            xs.append(x)
            ys.append(y)
    creature_x            = np.array(xs, dtype=np.int32)
    creature_y            = np.array(ys, dtype=np.int32)
    creature_hp           = np.full(count, 100, dtype=np.int32)
    creature_gold         = np.zeros(count, dtype=np.int32)
    creature_age          = np.zeros(count, dtype=np.int32)
    creature_status       = np.zeros(count, dtype=np.float32)
    creature_traits       = np.random.uniform(0.25, 0.75, size=(count, len(TRAIT_NAMES))).astype(np.float32)
    creature_last_action  = [""] * count
    creature_last_interaction = [""] * count
    creature_score        = np.zeros(count, dtype=np.float32)

def gold_field_delta(x, y, nx, ny):
    return nearest_gold_distance(x, y) - nearest_gold_distance(nx, ny)

def status_field_delta(x, y, nx, ny):
    return local_status_field(nx, ny) - local_status_field(x, y)

def space_field_delta(x, y, nx, ny):
    density_here = sum(1 for j in range(len(creature_x)) if abs(int(creature_x[j]) - x) + abs(int(creature_y[j]) - y) <= 3)
    density_next = sum(1 for j in range(len(creature_x)) if abs(int(creature_x[j]) - nx) + abs(int(creature_y[j]) - ny) <= 3)
    return density_here - density_next

def novelty_field_delta(x, y, nx, ny):
    return int(world_visit[y, x]) - int(world_visit[ny, nx])

def openness_field(nx, ny):
    return count_open_neighbors(nx, ny) / 4.0

def composite_field_value(i, nx, ny):
    x, y = int(creature_x[i]), int(creature_y[i])
    t = creature_traits[i]
    wealth_drive    = float(t[0])
    status_drive    = float(t[1])
    social_distance = float(t[2])
    curiosity       = float(t[3])
    caution         = float(t[4])
    value = (
        wealth_drive    * gold_field_delta(x, y, nx, ny)   +
        status_drive    * status_field_delta(x, y, nx, ny) +
        social_distance * space_field_delta(x, y, nx, ny)  +
        curiosity       * novelty_field_delta(x, y, nx, ny)+
        caution         * openness_field(nx, ny)
    )
    return value

def choose_move(i):
    x, y = int(creature_x[i]), int(creature_y[i])
    best_value = None
    best_cells = []
    for dx, dy in NEIGHBOR_DELTAS:
        nx, ny = x + dx, y + dy
        if is_blocked(nx, ny):
            continue
        val = composite_field_value(i, nx, ny)
        if best_value is None or val > best_value:
            best_value = val
            best_cells = [(nx, ny)]
        elif val == best_value:
            best_cells.append((nx, ny))
    if not best_cells:
        return x, y
    return random.choice(best_cells)

def _effect_mug(i, j):
    creature_gold[j] -= 1
    creature_gold[i] += 1
    creature_status[i] = np.clip(creature_status[i] + 0.3, 0.0, 10.0)
    creature_score[i] += 1.5
    print(f"[creature {i}] mugged creature {j}")

def _effect_display(i, j):
    winner = i if float(creature_status[i]) >= float(creature_status[j]) else j
    loser  = j if winner == i else i
    creature_status[winner] = np.clip(creature_status[winner] + 0.2, 0.0, 10.0)
    creature_status[loser]  = np.clip(creature_status[loser]  - 0.1, 0.0, 10.0)
    creature_score[winner] += 0.5
    print(f"[creature {i}] status display with {j}: winner={winner}")

def _effect_yield(i, j):
    creature_status[j] = np.clip(creature_status[j] + 0.15, 0.0, 10.0)
    creature_score[j] += 0.3
    print(f"[creature {i}] yielded to creature {j}")

def _effect_gift(i, j):
    creature_gold[i] -= 1
    creature_gold[j] += 1
    creature_status[i] = np.clip(creature_status[i] + 0.25, 0.0, 10.0)
    creature_score[i] += 0.4
    print(f"[creature {i}] gifted gold to creature {j}")

def _effect_challenge(i, j):
    power_i = float(creature_status[i]) + float(creature_traits[i, 5]) + random.random()
    power_j = float(creature_status[j]) + float(creature_traits[j, 5]) + random.random()
    winner = i if power_i >= power_j else j
    loser  = j if winner == i else i
    creature_hp[loser]  = max(0, int(creature_hp[loser]) - random.randint(5, 20))
    creature_status[winner] = np.clip(creature_status[winner] + 0.4, 0.0, 10.0)
    creature_status[loser]  = np.clip(creature_status[loser]  - 0.2, 0.0, 10.0)
    creature_score[winner] += 1.0
    print(f"[creature {i}] challenged creature {j}: winner={winner}")

INTERACTION_MODES = {
    "mug": {
        "description": "steal gold from the weaker creature",
        "precondition": lambda i, j: float(creature_traits[i, 5]) > 0.55 and int(creature_gold[j]) > 0,
        "effect": _effect_mug,
    },
    "display": {
        "description": "assert dominance through posturing",
        "precondition": lambda i, j: float(creature_traits[i, 1]) > 0.5 and float(creature_traits[j, 1]) > 0.5,
        "effect": _effect_display,
    },
    "yield": {
        "description": "submit to the more powerful creature",
        "precondition": lambda i, j: float(creature_status[i]) < float(creature_status[j]) and float(creature_traits[i, 4]) > 0.55,
        "effect": _effect_yield,
    },
    "gift": {
        "description": "transfer gold to gain social standing",
        "precondition": lambda i, j: float(creature_traits[i, 1]) > 0.6 and int(creature_gold[i]) > 0,
        "effect": _effect_gift,
    },
    "challenge": {
        "description": "fight the other creature for dominance",
        "precondition": lambda i, j: float(creature_traits[i, 5]) > 0.65,
        "effect": _effect_challenge,
    },
}

def build_interaction_prompt(i, j):
    eligible = [
        (name, info["description"])
        for name, info in INTERACTION_MODES.items()
        if info["precondition"](i, j)
    ]
    if not eligible:
        return None, []
    options_text = "; ".join(f"{name}: {desc}" for name, desc in eligible)
    prompt = (
        f"You are in a grid game simulation. "
        f"Two creatures meet. "
        f"Creature {i}: hp={int(creature_hp[i])}, gold={int(creature_gold[i])}, "
        f"status={float(creature_status[i]):.2f}, "
        f"aggression={float(creature_traits[i, 5]):.2f}, "
        f"caution={float(creature_traits[i, 4]):.2f}. "
        f"Creature {j}: hp={int(creature_hp[j])}, gold={int(creature_gold[j])}, "
        f"status={float(creature_status[j]):.2f}. "
        f"Eligible interactions: {options_text}. "
        f"Reply with exactly one interaction name from the list, nothing else."
    )
    return prompt, [name for name, _ in eligible]

def handle_proximity_events(i):
    x, y = int(creature_x[i]), int(creature_y[i])
    others = nearby_creatures(i, x, y)
    if not others:
        return
    nearest_dist, j, ox, oy = others[0]
    if nearest_dist > 1:
        return
    prompt, eligible_names = build_interaction_prompt(i, j)
    if not eligible_names:
        return
    if getattr(settings, "ENABLE_LLM_INTERACTIONS", True):
        print(f"[interaction {i},{j}] prompt: {prompt}")
        response = ask_llm(prompt).strip().lower()
        chosen = next((name for name in eligible_names if name in response), eligible_names[0])
    else:
        chosen = eligible_names[0]
    print(f"[interaction {i},{j}] mode: {chosen}")
    creature_last_interaction[i] = chosen
    INTERACTION_MODES[chosen]["effect"](i, j)

def check_gold_pickup(i):
    pos = (int(creature_x[i]), int(creature_y[i]))
    if pos in gold_positions:
        gold_positions.discard(pos)
        creature_gold[i] += 1
        creature_status[i] = np.clip(creature_status[i] + 1.0, 0.0, 10.0)
        gold_respawn_timer[pos] = GOLD_RESPAWN_TICKS
        creature_score[i] += 2.0
        print(f"[creature {i}] picked up gold at {pos}, total={int(creature_gold[i])}")

def accumulate_survival_score(i):
    creature_score[i] += (int(creature_hp[i]) / 100.0) * 0.1 + int(creature_gold[i]) * 0.05
    creature_status[i] = np.clip(creature_status[i] + 0.01, 0.0, 10.0)

def tick_status_decay():
    global creature_status
    creature_status = np.clip(creature_status - STATUS_DECAY, 0.0, 10.0)

def apply_personality_feedback(i, moved, nx, ny):
    if not getattr(settings, "ENABLE_PERSONALITY_LEARNING", False):
        return
    x, y = int(creature_x[i]), int(creature_y[i])
    lr = 0.001
    if moved:
        creature_traits[i, 0] = np.clip(creature_traits[i, 0] + lr * gold_field_delta(x, y, nx, ny),    0.0, 1.0)
        creature_traits[i, 1] = np.clip(creature_traits[i, 1] + lr * status_field_delta(x, y, nx, ny),  0.0, 1.0)
        creature_traits[i, 2] = np.clip(creature_traits[i, 2] + lr * space_field_delta(x, y, nx, ny),   0.0, 1.0)
        creature_traits[i, 3] = np.clip(creature_traits[i, 3] + lr * novelty_field_delta(x, y, nx, ny), 0.0, 1.0)
        creature_traits[i, 4] = np.clip(creature_traits[i, 4] - lr * 0.5,                               0.0, 1.0)
    else:
        creature_traits[i, 4] = np.clip(creature_traits[i, 4] + lr * 0.5, 0.0, 1.0)

def apply_generational_nudge():
    n = len(creature_x)
    if n < 2:
        return
    best_i      = int(np.argmax(creature_score))
    best_traits = creature_traits[best_i].copy()
    nudge       = getattr(settings, "GENERATION_NUDGE_RATE", 0.02)
    for i in range(n):
        if i == best_i:
            continue
        creature_traits[i] = np.clip(
            creature_traits[i] * (1.0 - nudge) + best_traits * nudge,
            0.0, 1.0
        )
    creature_score[:] = 0.0
    print(f"[generation] nudged toward creature {best_i}: {best_traits.tolist()}")

def update_creature(i):
    x, y = int(creature_x[i]), int(creature_y[i])
    nx, ny = choose_move(i)
    moved = (nx != x or ny != y)
    if moved:
        creature_x[i] = nx
        creature_y[i] = ny
        world_visit[ny, nx] += 1
    creature_last_action[i] = f"({nx},{ny})"
    creature_age[i] += 1
    check_gold_pickup(i)
    handle_proximity_events(i)
    accumulate_survival_score(i)
    apply_personality_feedback(i, moved, nx, ny)

def update_creatures():
    global _tick_counter
    tick_gold_respawn()
    tick_status_decay()
    for i in range(len(creature_x)):
        update_creature(i)
    _tick_counter += 1
    if _tick_counter % GENERATION_TICKS == 0:
        apply_generational_nudge()
