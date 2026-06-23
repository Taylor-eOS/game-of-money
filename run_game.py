import pygame
import sys
import game_logic
import sprites
import settings

pygame.init()
CELL_W = settings.SCALE
CELL_H = settings.SCALE
WIDTH  = settings.COLS * CELL_W
HEIGHT = settings.ROWS * CELL_H

def init_display():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Game of Money")
    return screen

GOLD_COLOR = (255, 215, 0)

def create_world_surface():
    surf = pygame.Surface((WIDTH, HEIGHT)).convert()
    surf.fill((255, 255, 255))
    for block_x, block_y in game_logic.world_blocks:
        pygame.draw.rect(surf, (100, 100, 100),
                         pygame.Rect(block_x * CELL_W, block_y * CELL_H, CELL_W, CELL_H))
    for gx, gy in game_logic.gold_positions:
        pygame.draw.rect(surf, GOLD_COLOR,
                         pygame.Rect(gx * CELL_W, gy * CELL_H, CELL_W, CELL_H))
    return surf

def status_to_color(status_val, max_status=10.0):
    t = min(float(status_val) / max_status, 1.0)
    r = int(50  + (205 * t))
    g = int(200 - (150 * t))
    b = int(50)
    return (r, g, b)

def render_frame(screen, world_surf):
    screen.blit(world_surf, (0, 0))
    n = len(game_logic.creature_x)
    for i in range(n):
        cx = int(game_logic.creature_x[i]) * CELL_W
        cy = int(game_logic.creature_y[i]) * CELL_H
        shirt = status_to_color(game_logic.creature_status[i])
        surf = sprites.create_creature_surfaces(CELL_W, CELL_H, shirt)
        screen.blit(surf, (cx, cy))
    pygame.display.flip()

def handle_events():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

def main():
    screen = init_display()
    game_logic.init_world()
    game_logic.spawn_creatures(4)
    clock = pygame.time.Clock()
    while True:
        handle_events()
        game_logic.update_creatures()
        world_surf = create_world_surface()
        render_frame(screen, world_surf)
        clock.tick(settings.SPEED)

if __name__ == "__main__":
    main()
