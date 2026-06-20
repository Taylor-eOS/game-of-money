import pygame
import sys
import random
import settings

pygame.init()
CELL_W = settings.SPRITE_W * settings.SCALE
CELL_H = settings.SPRITE_H * settings.SCALE
WIDTH = settings.COLS * CELL_W
HEIGHT = settings.ROWS * CELL_H

class Creature:
    def __init__(self, x, y, sprite_surf, flipped_surf):
        self.x = x
        self.y = y
        self.sprite_surf = sprite_surf
        self.flipped_surf = flipped_surf
        self.flipped = False

    def move(self):
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        self.x = (self.x + dx) % settings.COLS
        self.y = (self.y + dy) % settings.ROWS

def init_display():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Game of Money")
    return screen

def create_creature_surfaces():
    sprite_surf = pygame.Surface((settings.SPRITE_W * settings.SCALE, settings.SPRITE_H * settings.SCALE), pygame.SRCALPHA)
    sprite_surf.fill((0, 0, 0, 0))
    for r in range(settings.SPRITE_H):
        for c in range(settings.SPRITE_W):
            if settings.sprite[r][c] == 1:
                rect = pygame.Rect(c * settings.SCALE, r * settings.SCALE, settings.SCALE, settings.SCALE)
                pygame.draw.rect(sprite_surf, (0, 0, 0), rect)
    flipped_surf = pygame.transform.flip(sprite_surf, True, False)
    return sprite_surf, flipped_surf

def spawn_creatures(count, sprite_surf, flipped_surf):
    creatures = []
    for _ in range(count):
        x = random.randint(0, settings.COLS - 1)
        y = random.randint(0, settings.ROWS - 1)
        creatures.append(Creature(x, y, sprite_surf, flipped_surf))
    return creatures

def render_frame(screen, creatures):
    screen.fill((255, 255, 255))
    for creature in creatures:
        surf = creature.sprite_surf if not creature.flipped else creature.flipped_surf
        screen.blit(surf, (creature.x * CELL_W, creature.y * CELL_H))
    pygame.display.flip()

def update_creatures(creatures):
    for creature in creatures:
        creature.move()

def handle_events():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

def main():
    screen = init_display()
    sprite_surf, flipped_surf = create_creature_surfaces()
    creatures = spawn_creatures(4, sprite_surf, flipped_surf)
    clock = pygame.time.Clock()
    while True:
        handle_events()
        update_creatures(creatures)
        render_frame(screen, creatures)
        clock.tick(5)

if __name__ == "__main__":
    main()
