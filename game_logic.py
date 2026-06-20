import random
import settings

class World:
    def __init__(self):
        self.blocks = set()
        if hasattr(settings, 'WALLS'):
            for x1, y1, x2, y2 in settings.WALLS:
                self.add_wall(x1, y1, x2, y2)

    def add_wall(self, x1, y1, x2, y2):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                self.blocks.add((x, y))

    def is_blocked(self, x, y, width, height):
        if x < 0 or y < 0 or x + width > settings.COLS or y + height > settings.ROWS:
            return True
        for bx in range(x, x + width):
            for by in range(y, y + height):
                if (bx, by) in self.blocks:
                    return True
        return False

class Creature:
    def __init__(self, x, y, sprite_surf, flipped_surf):
        self.x = x
        self.y = y
        self.width = settings.SPRITE_W
        self.height = settings.SPRITE_H
        self.sprite_surf = sprite_surf
        self.flipped_surf = flipped_surf
        self.flipped = False

    def move(self, world):
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        new_x = self.x + dx
        new_y = self.y + dy
        if not world.is_blocked(new_x, new_y, self.width, self.height):
            self.x = new_x
            self.y = new_y
            if dx != 0:
                self.flipped = dx < 0

def spawn_creatures(count, sprite_surf, flipped_surf, world):
    creatures = []
    for _ in range(count):
        while True:
            x = random.randint(0, settings.COLS - settings.SPRITE_W)
            y = random.randint(0, settings.ROWS - settings.SPRITE_H)
            if not world.is_blocked(x, y, settings.SPRITE_W, settings.SPRITE_H):
                creatures.append(Creature(x, y, sprite_surf, flipped_surf))
                break
    return creatures

def update_creatures(creatures, world):
    for creature in creatures:
        creature.move(world)

