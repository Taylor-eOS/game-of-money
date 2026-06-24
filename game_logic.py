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
TRAIT_NAMES = ("wealth_drive", "status_drive", "social_distance", "curiosity", "caution", "aggression")
DIRECTIONS = ("north", "south", "east", "west")
DIRECTION_DELTAS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
NEIGHBOR_DELTAS = ((0, -1), (0, 1), (1, 0), (-1, 0))
GENERATION_TICKS = getattr(settings, "GENERATION_TICKS", 200)
STATUS_DECAY = getattr(settings, "STATUS_DECAY", 0.005)
STATUS_RADIUS = getattr(settings, "STATUS_RADIUS", 6)
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
        if 0 < dist <= STATUS_RADIUS:
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

def gold_field_delta(x, y, nx, ny):
    return world.nearest_gold_distance(x, y) - world.nearest_gold_distance(nx, ny)

def status_field_delta(x, y, nx, ny):
    return local_status_field(nx, ny) - local_status_field(x, y)

def space_field_delta(x, y, nx, ny):
    density_here = sum(1 for j in range(len(creature_x)) if creature_alive[j] and abs(int(creature_x[j]) - x) + abs(int(creature_y[j]) - y) <= 3)
    density_next = sum(1 for j in range(len(creature_x)) if creature_alive[j] and abs(int(creature_x[j]) - nx) + abs(int(creature_y[j]) - ny) <= 3)
    return density_here - density_next

def novelty_field_delta(x, y, nx, ny):
    return int(world.world_visit[y, x]) - int(world.world_visit[ny, nx])

def openness_field(nx, ny):
    return world.count_open_neighbors(nx, ny) / 4.0

def composite_field_value(i, nx, ny):
    x, y = int(creature_x[i]), int(creature_y[i])
    t = creature_traits[i]
    wealth_drive = float(t[0])
    status_drive = float(t[1])
    social_distance = float(t[2])
    curiosity = float(t[3])
    caution = float(t[4])
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
    target = choose_target(i)
    best_value = None
    best_cells = []
    for dx, dy in NEIGHBOR_DELTAS:
        nx, ny = x + dx, y + dy
        if world.is_blocked(nx, ny):
            continue
        val = target_field_value(i, target, nx, ny)
        if best_value is None or val > best_value:
            best_value = val
            best_cells = [(nx, ny)]
        elif val == best_value:
            best_cells.append((nx, ny))
    if not best_cells:
        return x, y
    return random.choice(best_cells)

def choose_target(i):
    return {"type": "composite"}

def composite_field_value(i, nx, ny):
    x, y = int(creature_x[i]), int(creature_y[i])
    t = creature_traits[i]
    wealth_drive = float(t[0])
    status_drive = float(t[1])
    social_distance = float(t[2])
    curiosity = float(t[3])
    caution = float(t[4])
    value = (
        wealth_drive * gold_field_delta(x, y, nx, ny) +
        status_drive * status_field_delta(x, y, nx, ny) +
        social_distance * space_field_delta(x, y, nx, ny) +
        curiosity * novelty_field_delta(x, y, nx, ny) +
        caution * openness_field(nx, ny)
    )
    return value

def target_field_value(i, target, nx, ny):
    target_type = target["type"]
    if target_type == "composite":
        return composite_field_value(i, nx, ny)
    return 0.0

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
        f"You are narrating a grid world simulation. Two creatures meet and {desc}. "
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

INTERACTION_CHANCE = getattr(settings, "INTERACTION_CHANCE", 0.4)

def handle_proximity_events(i):
    x, y = int(creature_x[i]), int(creature_y[i])
    others = nearby_creatures(i, x, y)
    if not others:
        return
    nearest_dist, j, ox, oy = others[0]
    if nearest_dist > 1:
        return
    if random.random() > INTERACTION_CHANCE:
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
    if getattr(settings, "ENABLE_LLM_INTERACTIONS", True):
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
    alive_indices = [i for i in range(len(creature_x)) if creature_alive[i]]
    if len(alive_indices) < 2:
        return
    best_i = alive_indices[int(np.argmax(creature_score[alive_indices]))]
    best_traits = creature_traits[best_i].copy()
    nudge = getattr(settings, "GENERATION_NUDGE_RATE", 0.02)
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
    if _tick_counter % GENERATION_TICKS == 0:
        apply_generational_nudge()

