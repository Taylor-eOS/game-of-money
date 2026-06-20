import pygame
import sys
import settings
import game_logic

pygame.init()
CELL_W = settings.SCALE
CELL_H = settings.SCALE
WIDTH = settings.COLS * CELL_W
HEIGHT = settings.ROWS * CELL_H

def init_display():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Game of Money")
    return screen

def create_creature_surfaces():
    sprite_surf = pygame.Surface((settings.SPRITE_W * CELL_W, settings.SPRITE_H * CELL_H), pygame.SRCALPHA)
    sprite_surf.fill((0, 0, 0, 0))
    for r in range(settings.SPRITE_H):
        for c in range(settings.SPRITE_W):
            if settings.sprite[r][c] == 1:
                rect = pygame.Rect(c * CELL_W, r * CELL_H, CELL_W, CELL_H)
                pygame.draw.rect(sprite_surf, (0, 0, 0), rect)
    flipped_surf = pygame.transform.flip(sprite_surf, True, False)
    return sprite_surf, flipped_surf

def render_frame(screen, creatures, world):
    screen.fill((255, 255, 255))
    for block_x, block_y in world.blocks:
        rect = pygame.Rect(block_x * CELL_W, block_y * CELL_H, CELL_W, CELL_H)
        pygame.draw.rect(screen, (100, 100, 100), rect)
    for creature in creatures:
        surf = creature.sprite_surf if not creature.flipped else creature.flipped_surf
        screen.blit(surf, (creature.x * CELL_W, creature.y * CELL_H))
    pygame.display.flip()

def handle_events():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

def main():
    screen = init_display()
    sprite_surf, flipped_surf = create_creature_surfaces()
    world = game_logic.World()
    creatures = game_logic.spawn_creatures(4, sprite_surf, flipped_surf, world)
    clock = pygame.time.Clock()
    while True:
        handle_events()
        game_logic.update_creatures(creatures, world)
        render_frame(screen, creatures, world)
        clock.tick(5)

if __name__ == "__main__":
    main()

