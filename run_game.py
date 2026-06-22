import pygame
import sys
import game_logic
import settings
import sprites

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
    # This is now called every frame (cheap since gold changes), 
    # or you can keep a dirty flag. Simplest: just redraw.
    surf = pygame.Surface((WIDTH, HEIGHT)).convert()
    surf.fill((255, 255, 255))
    for block_x, block_y in game_logic.world_blocks:
        pygame.draw.rect(surf, (100, 100, 100),
                         pygame.Rect(block_x * CELL_W, block_y * CELL_H, CELL_W, CELL_H))
    for gx, gy in game_logic.gold_positions:
        pygame.draw.rect(surf, GOLD_COLOR,
                         pygame.Rect(gx * CELL_W, gy * CELL_H, CELL_W, CELL_H))
    return surf

def update_blit_list(blit_list):
    for i, entry in enumerate(blit_list):
        entry[1].x = int(game_logic.creature_x[i]) * CELL_W
        entry[1].y = int(game_logic.creature_y[i]) * CELL_H

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
    game_logic.init_world()
    game_logic.spawn_creatures(4)
    blit_list = sprites.build_blit_list(CELL_W, CELL_H, game_logic.creature_x, game_logic.creature_y)
    clock = pygame.time.Clock()
    while True:
        handle_events()
        game_logic.update_creatures()
        world_surf = create_world_surface()   # rebuild each frame to show gold changes
        update_blit_list(blit_list)
        render_frame(screen, world_surf, blit_list)
        clock.tick(settings.SPEED)

if __name__ == "__main__":
    main()
