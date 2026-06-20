import pygame
import sys
import game_logic
import settings

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
    sprite = pygame.Surface((CELL_W, CELL_H), pygame.SRCALPHA)
    size = max(2, int(min(CELL_W, CELL_H) * 0.7))
    offset_x = (CELL_W - size) // 2
    offset_y = (CELL_H - size) // 2
    body_rect = pygame.Rect(offset_x, offset_y, size, size)
    pygame.draw.ellipse(sprite, (0, 0, 0), body_rect)
    eye_size = max(1, size // 5)
    eye_rect = pygame.Rect(body_rect.right - eye_size * 2, body_rect.top + eye_size, eye_size, eye_size)
    pygame.draw.rect(sprite, (255, 255, 255), eye_rect)
    flipped = pygame.transform.flip(sprite, True, False)
    return sprite.convert_alpha(), flipped.convert_alpha()

def create_world_surface(world):
    surf = pygame.Surface((WIDTH, HEIGHT)).convert()
    surf.fill((255, 255, 255))
    for block_x, block_y in world.blocks:
        pygame.draw.rect(surf, (100, 100, 100),
                         pygame.Rect(block_x * CELL_W, block_y * CELL_H, CELL_W, CELL_H))
    return surf

def build_blit_list(creatures, surfs):
    return [[surfs[c.flipped], pygame.Rect(c.x * CELL_W, c.y * CELL_H, CELL_W, CELL_H)]
            for c in creatures]

def update_blit_list(blit_list, creatures, surfs):
    for entry, c in zip(blit_list, creatures):
        entry[0] = surfs[c.flipped]
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
    sprite_surf, flipped_surf = create_creature_surfaces()
    surfs = {False: sprite_surf, True: flipped_surf}
    world = game_logic.World()
    world_surf = create_world_surface(world)
    creatures = game_logic.spawn_creatures(4, world)
    blit_list = build_blit_list(creatures, surfs)
    clock = pygame.time.Clock()
    while True:
        handle_events()
        game_logic.update_creatures(creatures, world)
        update_blit_list(blit_list, creatures, surfs)
        render_frame(screen, world_surf, blit_list)
        clock.tick(5)

if __name__ == "__main__":
    main()

