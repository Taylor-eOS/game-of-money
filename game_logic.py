import numpy as np
import random
import re
import settings
from gguf_llm_library import ask_llm

creature_x = np.empty(0, dtype=np.int32)
creature_y = np.empty(0, dtype=np.int32)
creature_hp = np.empty(0, dtype=np.int32)
creature_gold = np.empty(0, dtype=np.int32)
creature_age = np.empty(0, dtype=np.int32)
creature_traits = np.empty((0, 6), dtype=np.float32)
creature_last_action = []
creature_last_intent = []
creature_score = np.empty(0, dtype=np.float32)
world_blocks = set()
world_areas = []
gold_positions = set()
gold_respawn_timer = {}
TRAIT_NAMES = ("wealth_drive", "status_drive", "social_distance", "curiosity", "caution", "aggression")
DIRECTIONS = ("north", "south", "east", "west")
DIRECTION_DELTAS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
GOLD_COUNT         = getattr(settings, "GOLD_COUNT", 12)
GOLD_RESPAWN_TICKS = getattr(settings, "GOLD_RESPAWN_TICKS", 30)
GENERATION_TICKS   = getattr(settings, "GENERATION_TICKS", 200)
_tick_counter = 0
BEHAVIORAL_MODES = {
    "seek_gold"     : (4.0,  0.0,  0.0,  0.5,  0.0,  0.0),
    "seek_company"  : (0.0,  3.0,  0.0,  0.5,  0.0,  0.0),
    "seek_space"    : (0.0,  0.0,  3.0,  1.0,  1.0,  0.0),
    "explore"       : (0.5,  0.0,  0.5,  3.0,  0.0,  0.0),
    "be_cautious"   : (0.0,  0.0,  2.0,  0.5,  3.0,  0.0),
    "be_aggressive" : (0.0,  0.0,  0.0,  0.0,  0.0,  4.0),
    "idle"          : (0.5,  0.5,  0.5,  0.5,  0.5,  0.5),
}
MODE_KEYWORDS = [
    ("seek_gold",     ["gold", "wealth", "rich", "money", "coin", "earn", "grab"]),
    ("seek_company",  ["company", "social", "crowd", "together", "status", "seen", "dominant", "group", "presence"]),
    ("seek_space",    ["space", "alone", "distance", "away", "solitude", "avoid", "escape", "flee"]),
    ("explore",       ["explore", "curious", "wander", "discover", "unknown", "new"]),
    ("be_cautious",   ["cautious", "careful", "safe", "danger", "threat", "low hp", "hurt", "weak"]),
    ("be_aggressive", ["aggress", "attack", "confront", "fight", "dominate", "challenge", "hunt", "chase"]),
]

def classify_intent(text: str) -> str:
    lower = text.lower()
    for mode, keywords in MODE_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return mode
    return "idle"

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

def gold_gradient(x, y, direction):
    dx, dy = DIRECTION_DELTAS[direction]
    nx, ny = x + dx, y + dy
    return nearest_gold_distance(x, y) - nearest_gold_distance(nx, ny)

def spawn_creatures(count):
    global creature_x, creature_y, creature_hp, creature_gold, creature_age
    global creature_traits, creature_last_action, creature_last_intent, creature_score
    xs, ys = [], []
    while len(xs) < count:
        x = random.randint(0, settings.COLS - 1)
        y = random.randint(0, settings.ROWS - 1)
        if not is_blocked(x, y):
            xs.append(x)
            ys.append(y)
    creature_x      = np.array(xs, dtype=np.int32)
    creature_y      = np.array(ys, dtype=np.int32)
    creature_hp     = np.full(count, 100, dtype=np.int32)
    creature_gold   = np.zeros(count, dtype=np.int32)
    creature_age    = np.zeros(count, dtype=np.int32)
    creature_traits = np.random.uniform(0.25, 0.75, size=(count, len(TRAIT_NAMES))).astype(np.float32)
    creature_last_action = [""] * count
    creature_last_intent = [""] * count
    creature_score  = np.zeros(count, dtype=np.float32)

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

def count_open_neighbors(x, y):
    return sum(
        1 for dx, dy in ((0, -1), (0, 1), (1, 0), (-1, 0))
        if not is_blocked(x + dx, y + dy)
    )

def nearest_creature_distance(i, x, y):
    best = None
    for j in range(len(creature_x)):
        if j == i:
            continue
        dist = abs(int(creature_x[j]) - x) + abs(int(creature_y[j]) - y)
        if best is None or dist < best:
            best = dist
    return best if best is not None else max(settings.COLS, settings.ROWS)

def creature_density(x, y, radius=3):
    return sum(
        1 for j in range(len(creature_x))
        if abs(int(creature_x[j]) - x) + abs(int(creature_y[j]) - y) <= radius
    )

def trait_summary(i):
    t = creature_traits[i]
    dominant = TRAIT_NAMES[int(np.argmax(t))]
    return f"dominant trait: {dominant} ({t.max():.2f})"

def situational_sentence(i):
    x, y  = int(creature_x[i]), int(creature_y[i])
    hp    = int(creature_hp[i])
    gold  = int(creature_gold[i])
    gdist = nearest_gold_distance(x, y)
    others = nearby_creatures(i, x, y)
    nearest_dist = others[0][0] if others else 999
    parts = []
    if hp < 40:
        parts.append("you are badly hurt")
    elif hp < 70:
        parts.append("you are wounded")
    if gold > 0:
        parts.append(f"you are carrying {gold} gold")
    if gdist <= 5:
        parts.append(f"gold is very close ({gdist} steps)")
    elif gdist <= 15:
        parts.append(f"gold is nearby ({gdist} steps)")
    if nearest_dist <= 4:
        parts.append(f"another creature is right next to you ({nearest_dist} steps)")
    elif nearest_dist <= 12:
        parts.append(f"a creature is nearby ({nearest_dist} steps)")
    if not parts:
        parts.append("the area is quiet and open")
    return "; ".join(parts)

def summarize_local_context(i):
    x, y  = int(creature_x[i]), int(creature_y[i])
    hp    = int(creature_hp[i])
    gold  = int(creature_gold[i])
    age   = int(creature_age[i])
    area  = get_area(x, y)
    lines = [f"state: hp={hp}, gold={gold}, age={age}"]
    if area:
        lines.append(f"area: {area}")
    lines.append(trait_summary(i))
    lines.append(f"situation: {situational_sentence(i)}")
    if creature_last_intent[i]:
        lines.append(f"last_intent: {creature_last_intent[i]}")
    others = nearby_creatures(i, x, y)
    if others:
        near = [f"creature{j} dist={dist}" for dist, j, ox, oy in others[:3]]
        lines.append("nearby: " + "; ".join(near))
    gd = nearest_gold_distance(x, y)
    lines.append(f"nearest_gold: {gd} steps")
    for direction in DIRECTIONS:
        dx, dy = DIRECTION_DELTAS[direction]
        nx, ny = x + dx, y + dy
        if is_blocked(nx, ny):
            lines.append(f"{direction}: blocked")
        else:
            gdelta = gold_gradient(x, y, direction)
            cdist  = nearest_creature_distance(i, nx, ny)
            tag = ""
            if gdelta > 0:
                tag += " [toward gold]"
            if cdist < nearest_creature_distance(i, x, y):
                tag += " [toward creature]"
            lines.append(f"{direction}: open{tag}")
    return " | ".join(lines)

def ask_intent_llm(i):
    context = summarize_local_context(i)
    prompt = (
        "You are the inner voice of a small creature in a social simulation. "
        "Given the situation below, write ONE short phrase (under ten words) describing "
        "what the creature feels like doing right now. Be specific to the situation. "
        "Examples: 'go grab that gold', 'get away from the crowd', 'wander and see what's out there', "
        "'stay cautious, I'm hurt', 'get closer and make my presence known'. "
        f"Situation: {context}"
    )
    print(f"[creature {i}] prompt: {prompt}")
    response = ask_llm(prompt).strip()
    response = response.strip('"\'')
    print(f"[creature {i}] intent: {response!r}")
    return response

def score_direction(i, direction, mode_coeffs):
    x, y = int(creature_x[i]), int(creature_y[i])
    dx, dy = DIRECTION_DELTAS[direction]
    nx, ny = x + dx, y + dy
    if is_blocked(nx, ny):
        return -1e9
    gdelta    = float(gold_gradient(x, y, direction))
    density   = float(creature_density(nx, ny))
    cdist     = float(nearest_creature_distance(i, nx, ny))
    openness  = float(count_open_neighbors(nx, ny)) / 4.0
    proximity = 1.0 / (1.0 + cdist)
    gold_pull, crowd_pull, space_pull, open_pull, caution_pull, aggro_pull = mode_coeffs
    score = (
        gold_pull    * gdelta    +
        crowd_pull   * density   +
        space_pull   * cdist     +
        open_pull    * openness  +
        caution_pull * cdist     +
        aggro_pull   * proximity
    )
    return score

def get_mode_coefficients(i, mode: str):
    base = list(BEHAVIORAL_MODES.get(mode, BEHAVIORAL_MODES["idle"]))
    t = creature_traits[i]
    base[0] *= 0.5 + float(t[0])
    base[1] *= 0.5 + float(t[1])
    base[2] *= 0.5 + float(t[2])
    base[3] *= 0.5 + float(t[3])
    base[4] *= 0.5 + float(t[4])
    base[5] *= 0.5 + float(t[5])
    return tuple(base)

def choose_direction(i, mode: str):
    coeffs = get_mode_coefficients(i, mode)
    scored = [(score_direction(i, d, coeffs), d) for d in DIRECTIONS]
    best_score = max(s for s, _ in scored)
    best_dirs  = [d for s, d in scored if s == best_score]
    choice = random.choice(best_dirs)
    print(f"[creature {i}] mode={mode} scores={scored} -> {choice}")
    return choice

def decide_move(i):
    intent_text = ask_intent_llm(i)
    creature_last_intent[i] = intent_text
    mode = classify_intent(intent_text)
    print(f"[creature {i}] classified as: {mode}")
    direction = choose_direction(i, mode)
    return direction

def check_gold_pickup(i):
    pos = (int(creature_x[i]), int(creature_y[i]))
    if pos in gold_positions:
        gold_positions.discard(pos)
        creature_gold[i] += 1
        gold_respawn_timer[pos] = GOLD_RESPAWN_TICKS
        creature_score[i] += 2.0
        print(f"[creature {i}] picked up gold at {pos}, total={int(creature_gold[i])}")

def handle_proximity_events(i):
    x, y = int(creature_x[i]), int(creature_y[i])
    others = nearby_creatures(i, x, y)
    if not others:
        return
    nearest_dist, j, ox, oy = others[0]
    if nearest_dist > 1:
        return
    t_i = creature_traits[i]
    t_j = creature_traits[j]
    if t_i[5] > 0.6 and creature_gold[j] > 0:
        creature_gold[j] -= 1
        creature_gold[i] += 1
        creature_score[i] += 1.5
        print(f"[creature {i}] mugged creature {j} for 1 gold")
    if t_i[1] > 0.6 and t_j[1] > 0.6:
        creature_score[i] += 0.5
        creature_score[j] += 0.5
        print(f"[creature {i}] engaged in status display with creature {j}")

def accumulate_survival_score(i):
    creature_score[i] += (int(creature_hp[i]) / 100.0) * 0.1 + int(creature_gold[i]) * 0.05

def apply_personality_feedback(i, moved):
    if not getattr(settings, "ENABLE_PERSONALITY_LEARNING", False):
        return
    if moved:
        creature_traits[i, 3] = np.clip(creature_traits[i, 3] + 0.001,  0.0, 1.0)
        creature_traits[i, 4] = np.clip(creature_traits[i, 4] - 0.0005, 0.0, 1.0)
    else:
        creature_traits[i, 4] = np.clip(creature_traits[i, 4] + 0.0015, 0.0, 1.0)
        creature_traits[i, 3] = np.clip(creature_traits[i, 3] - 0.0005, 0.0, 1.0)

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
    direction = decide_move(i)
    creature_last_action[i] = direction
    dx, dy = DIRECTION_DELTAS[direction]
    nx = int(creature_x[i]) + dx
    ny = int(creature_y[i]) + dy
    moved = False
    if not is_blocked(nx, ny):
        creature_x[i] = nx
        creature_y[i] = ny
        moved = True
    creature_age[i] += 1
    check_gold_pickup(i)
    handle_proximity_events(i)
    accumulate_survival_score(i)
    apply_personality_feedback(i, moved)

def update_creatures():
    global _tick_counter
    tick_gold_respawn()
    for i in range(len(creature_x)):
        update_creature(i)
    _tick_counter += 1
    if _tick_counter % GENERATION_TICKS == 0:
        apply_generational_nudge()
