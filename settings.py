VISUAL_SCALE = 18
GOLD_SMALLNESS = 4
GRID_PART = 10
GRID_COLS = 10 * GRID_PART
GRID_ROWS = 5 * GRID_PART
CLOCK_SPEED = 50
CREATURE_COUNT = 22
CREATURE_SLOTS = 25
GOLD_COUNT = 15
CULL_INTERVAL = 40
PRINT_PICKUP = False
PRINT_INTERACTIONS = False
DENSITY_RADIUS = 5
DENSITY_NORM = 10.0
MUTATION_STD = 0.03
MUTATION_PROB = 0.05
HP_REGEN = 1

WALLS = [
    (10, 10, 30, 10),
    (30, 10, 30, 40),
    (30, 40, 20, 40),
    (80, 32, 80, GRID_ROWS - 1),
]
AREAS = [
    (10, 10, 30, 40, "inside"),
]

def _build_wall_cells():
    cells = set()
    for x1, y1, x2, y2 in WALLS:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                cells.add((x, y))
    return cells

WALL_CELLS = _build_wall_cells()

