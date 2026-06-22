import random
import re
import numpy as np
import settings
from gguf_llm_library import ask_llm

creature_x = np.empty(0, dtype=np.int32)
creature_y = np.empty(0, dtype=np.int32)
creature_hp = np.empty(0, dtype=np.int32)
creature_gold = np.empty(0, dtype=np.int32)
creature_age = np.empty(0, dtype=np.int32)
creature_traits = np.empty((0, 6), dtype=np.float32)
creature_last_action = []
world_blocks = set()
world_areas = []
TRAIT_NAMES = ("wealth_drive", "status_drive", "social_distance", "curiosity", "caution", "aggression")
DIRECTIONS = ("north", "south", "east", "west")

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
    global creature_x, creature_y, creature_hp, creature_gold, creature_age, creature_traits, creature_last_action
    xs, ys = [], []
    while len(xs) < count:
        x = random.randint(0, settings.COLS - 1)
        y = random.randint(0, settings.ROWS - 1)
        if not is_blocked(x, y):
            xs.append(x)
            ys.append(y)
    creature_x = np.array(xs, dtype=np.int32)
    creature_y = np.array(ys, dtype=np.int32)
    creature_hp = np.full(count, 100, dtype=np.int32)
    creature_gold = np.zeros(count, dtype=np.int32)
    creature_age = np.zeros(count, dtype=np.int32)
    creature_traits = np.random.uniform(0.25, 0.75, size=(count, len(TRAIT_NAMES))).astype(np.float32)
    creature_last_action = [""] * count

def get_creature_state(i):
    return {
        "index": i,
        "x": int(creature_x[i]),
        "y": int(creature_y[i]),
        "hp": int(creature_hp[i]),
        "gold": int(creature_gold[i]),
        "age": int(creature_age[i]),
        "area": get_area(int(creature_x[i]), int(creature_y[i])),
        "traits": {name: float(creature_traits[i, idx]) for idx, name in enumerate(TRAIT_NAMES)},
        "last_action": creature_last_action[i] if i < len(creature_last_action) else "",
    }

def trait_vector_to_text(i):
    return ", ".join(f"{name}={float(creature_traits[i, idx]):.2f}" for idx, name in enumerate(TRAIT_NAMES))

def parse_drive_weights(response):
    numbers = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", response)
    if len(numbers) < len(TRAIT_NAMES):
        return None
    values = [float(n) for n in numbers[:len(TRAIT_NAMES)]]
    return np.clip(np.array(values, dtype=np.float32), 0.0, 1.0)

def nearby_creatures(i, x, y):
    others = []
    for j in range(len(creature_x)):
        if j == i:
            continue
        ox = int(creature_x[j])
        oy = int(creature_y[j])
        dist = abs(ox - x) + abs(oy - y)
        others.append((dist, j, ox, oy))
    others.sort(key=lambda item: item[0])
    return others

def count_open_neighbors(x, y):
    count = 0
    for dx, dy in ((0, -1), (0, 1), (1, 0), (-1, 0)):
        if not is_blocked(x + dx, y + dy):
            count += 1
    return count

def nearest_creature_distance(i, x, y):
    best = None
    for j in range(len(creature_x)):
        if j == i:
            continue
        dist = abs(int(creature_x[j]) - x) + abs(int(creature_y[j]) - y)
        if best is None or dist < best:
            best = dist
    if best is None:
        return max(settings.COLS, settings.ROWS)
    return best

def summarize_local_context(i):
    x = int(creature_x[i])
    y = int(creature_y[i])
    hp = int(creature_hp[i])
    gold = int(creature_gold[i])
    age = int(creature_age[i])
    area = get_area(x, y)
    lines = [f"state: hp={hp}, gold={gold}, age={age}"]
    if area:
        lines.append(f"area: {area}")
    lines.append(f"personality: {trait_vector_to_text(i)}")
    if creature_last_action[i]:
        lines.append(f"last_action: {creature_last_action[i]}")
    others = nearby_creatures(i, x, y)
    if others:
        near = []
        for dist, j, ox, oy in others[:4]:
            near.append(f"creature{j}@({ox},{oy}) dist={dist}")
        lines.append("nearby_creatures: " + "; ".join(near))
    else:
        lines.append("nearby_creatures: none")
    for dx, dy, label in ((0, -1, "north"), (0, 1, "south"), (1, 0, "east"), (-1, 0, "west")):
        nx, ny = x + dx, y + dy
        if is_blocked(nx, ny):
            lines.append(f"direction_{label}: blocked")
        else:
            narea = get_area(nx, ny)
            dist = nearest_creature_distance(i, nx, ny)
            open_count = count_open_neighbors(nx, ny)
            desc = f"open dist_to_nearest_creature={dist} open_neighbors={open_count}"
            if narea and narea != area:
                desc += f" area={narea}"
            lines.append(f"direction_{label}: {desc}")
    return " | ".join(lines)

def ask_drive_weights(i):
    prompt = (
        "You are generating short-term drive weights for a simulated social creature. "
        "Return exactly six decimal numbers between 0 and 1, in this order: wealth_drive, status_drive, social_distance, curiosity, caution, aggression. "
        "Do not explain. "
        f"Base personality: {trait_vector_to_text(i)}. "
        f"Current context: {summarize_local_context(i)}"
    )
    print(f"[creature {i}] prompt: {prompt}")
    response = ask_llm(prompt).strip()
    print(f"[creature {i}] response: {response!r}")
    parsed = parse_drive_weights(response)
    if parsed is None:
        fallback = creature_traits[i].copy()
        print(f"[creature {i}] drive parse failed, using base personality: {fallback.tolist()}")
        return fallback
    print(f"[creature {i}] parsed drives: {parsed.tolist()}")
    return parsed

def blend_drive_weights(i, inferred_weights):
    base = creature_traits[i]
    blended = np.clip(base * 0.7 + inferred_weights * 0.3, 0.0, 1.0)
    hp = int(creature_hp[i])
    gold = int(creature_gold[i])
    if hp < 50:
        blended[4] = min(1.0, blended[4] + (50 - hp) / 100.0)
    if gold > 0:
        blended[0] = min(1.0, blended[0] + min(gold, 10) / 50.0)
    return blended

def score_direction(i, direction, weights):
    x = int(creature_x[i])
    y = int(creature_y[i])
    dx, dy = intent_to_delta(i, direction)
    nx = x + dx
    ny = y + dy
    if is_blocked(nx, ny):
        return -1e9
    nearest = nearest_creature_distance(i, nx, ny)
    open_neighbors = count_open_neighbors(nx, ny)
    interaction = 1.0 / (1.0 + float(nearest))
    space = float(open_neighbors) / 4.0
    score = 0.0
    score += float(weights[0]) * interaction
    score += float(weights[1]) * interaction
    score += float(weights[2]) * float(nearest)
    score += float(weights[3]) * space
    score += float(weights[4]) * (float(nearest) + space)
    score += float(weights[5]) * (1.0 - interaction)
    return score

def choose_direction(i, weights):
    scored = [(score_direction(i, d, weights), d) for d in DIRECTIONS]
    best_score = max(score for score, _ in scored)
    best = [direction for score, direction in scored if score == best_score]
    if not best:
        choice = random.choice(DIRECTIONS)
        print(f"[creature {i}] no legal best direction, random: {choice}")
        return choice
    choice = random.choice(best)
    print(f"[creature {i}] direction scores: {scored} -> {choice}")
    return choice

def ask_intent(i):
    inferred = ask_drive_weights(i)
    weights = blend_drive_weights(i, inferred)
    print(f"[creature {i}] blended drives: {weights.tolist()}")
    return choose_direction(i, weights)

def intent_to_delta(i, direction):
    return {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}[direction]

def apply_personality_feedback(i, moved):
    if not getattr(settings, "ENABLE_PERSONALITY_LEARNING", False):
        return
    if moved:
        creature_traits[i, 3] = np.clip(creature_traits[i, 3] + 0.001, 0.0, 1.0)
        creature_traits[i, 4] = np.clip(creature_traits[i, 4] - 0.0005, 0.0, 1.0)
    else:
        creature_traits[i, 4] = np.clip(creature_traits[i, 4] + 0.0015, 0.0, 1.0)
        creature_traits[i, 3] = np.clip(creature_traits[i, 3] - 0.0005, 0.0, 1.0)

def update_creature(i):
    response = ask_intent(i)
    creature_last_action[i] = response
    dx, dy = intent_to_delta(i, response)
    nx = int(creature_x[i]) + dx
    ny = int(creature_y[i]) + dy
    moved = False
    if not is_blocked(nx, ny):
        creature_x[i] = nx
        creature_y[i] = ny
        moved = True
    creature_age[i] += 1
    apply_personality_feedback(i, moved)

def update_creatures():
    for i in range(len(creature_x)):
        update_creature(i)
