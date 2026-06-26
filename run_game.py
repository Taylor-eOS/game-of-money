import sys
import pygame
import world
import game_logic
import sprites
import settings

pygame.init()
CELL_W = settings.GRID_SCALE
CELL_H = settings.GRID_SCALE
WIDTH = settings.GRID_COLS * CELL_W
HEIGHT = settings.GRID_ROWS * CELL_H
GOLD_COLOR = (255, 215, 0)

def init_display():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Game of Money")
    return screen

def draw_gold_shape(surf, grid_x, grid_y):
    center_x = grid_x * CELL_W + CELL_W // 2
    center_y = grid_y * CELL_H + CELL_H // 2
    radius = min(CELL_W, CELL_H) // settings.GOLD_SMALLNESS
    points = [(center_x, center_y - radius), (center_x + radius, center_y), (center_x, center_y + radius), (center_x - radius, center_y)]
    pygame.draw.polygon(surf, GOLD_COLOR, points)

def create_world_surface():
    surf = pygame.Surface((WIDTH, HEIGHT)).convert()
    surf.fill((255, 255, 255))
    for block_x, block_y in world.world_state.blocks:
        pygame.draw.rect(surf, (100, 100, 100),
                         pygame.Rect(block_x * CELL_W, block_y * CELL_H, CELL_W, CELL_H))
    for gx, gy in world.world_state.gold_positions:
        draw_gold_shape(surf, gx, gy)
    return surf

def render_frame(screen, world_surf):
    screen.blit(world_surf, (0, 0))
    n = len(game_logic.creature_state.x)
    for i in range(n):
        cx = int(game_logic.creature_state.x[i]) * CELL_W
        cy = int(game_logic.creature_state.y[i]) * CELL_H
        if game_logic.creature_state.alive[i]:
            screen.blit(sprites.creature_surfaces[i], (cx, cy))
        else:
            dead_surf = sprites.dead_surfaces[i]
            dw, dh = dead_surf.get_size()
            ox = cx + (CELL_W - dw) // 2
            oy = cy + (CELL_H - dh) // 2
            screen.blit(dead_surf, (ox, oy))
    pygame.display.flip()

def handle_events():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

def main():
    screen = init_display()
    world.init_world()
    game_logic.create_creatures(settings.CREATURE_COUNT)
    sprites.bake_creature_surfaces(settings.CREATURE_COUNT)
    clock = pygame.time.Clock()
    while True:
        handle_events()
        game_logic.update_creatures()
        world_surf = create_world_surface()
        render_frame(screen, world_surf)
        clock.tick(settings.CLOCK_SPEED)

if __name__ == "__main__":
    main()
