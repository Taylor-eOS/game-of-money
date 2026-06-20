import random
import settings

class World:
    def __init__(self):
        self.blocks = set()
        if hasattr(settings, "WALLS"):
            for x1, y1, x2, y2 in settings.WALLS:
                self.add_wall(x1, y1, x2, y2)

    def add_wall(self, x1, y1, x2, y2):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                self.blocks.add((x, y))

    def is_blocked(self, x, y):
        if x < 0 or y < 0 or x >= settings.COLS or y >= settings.ROWS:
            return True
        return (x, y) in self.blocks

class Creature:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.flipped = False

    def move(self, world):
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        nx = self.x + dx
        ny = self.y + dy
        if not world.is_blocked(nx, ny):
            self.x = nx
            self.y = ny
        if dx != 0:
            self.flipped = dx < 0

def spawn_creatures(count, world):
    creatures = []
    for _ in range(count):
        while True:
            x = random.randint(0, settings.COLS - 1)
            y = random.randint(0, settings.ROWS - 1)
            if not world.is_blocked(x, y):
                creatures.append(Creature(x, y))
                break
    return creatures

def update_creatures(creatures, world):
    for creature in creatures:
        creature.move(world)

