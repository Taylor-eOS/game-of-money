import pygame
import sys
import game_logic
import settings
import sprites

pygame.init()
CELL_W = settings.SCALE
CELL_H = settings.SCALE
WIDTH = settings.COLS * CELL_W
HEIGHT = settings.ROWS * CELL_H

def init_display():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Game of Money")
    return screen

def create_world_surface(world):
    surf = pygame.Surface((WIDTH, HEIGHT)).convert()
    surf.fill((255, 255, 255))
    for block_x, block_y in world.blocks:
        pygame.draw.rect(surf, (100, 100, 100),
                         pygame.Rect(block_x * CELL_W, block_y * CELL_H, CELL_W, CELL_H))
    return surf

def build_blit_list(creatures, surf):
    return [[surf, pygame.Rect(c.x * CELL_W, c.y * CELL_H, CELL_W, CELL_H)]
            for c in creatures]

def update_blit_list(blit_list, creatures):
    for entry, c in zip(blit_list, creatures):
        entry[1].x = c.x * CELL_W
        entry[1].y = c.y * CELL_H

def render_frame(screen, world_surf, blit_list):
    screen.blit(world_surf, (0, 0))
    screen.blits(blit_list)
    pygame.display.flip()

def handle_events():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

def main():
    screen = init_display()
    creature_surf = sprites.create_creature_surfaces(CELL_W, CELL_H)
    world = game_logic.World()
    world_surf = create_world_surface(world)
    creatures = game_logic.spawn_creatures(4, world)
    blit_list = build_blit_list(creatures, creature_surf)
    clock = pygame.time.Clock()
    while True:
        handle_events()
        game_logic.update_creatures(creatures, world)
        update_blit_list(blit_list, creatures)
        render_frame(screen, world_surf, blit_list)
        clock.tick(settings.SPEED)

if __name__ == "__main__":
    main()
