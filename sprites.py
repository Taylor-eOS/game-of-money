import pygame
import random

def random_shirt_color():
    return (random.randint(80, 220), random.randint(80, 220), random.randint(80, 220))

def create_creature_surface(cell_w, cell_h, shirt=(170, 70, 70)):
    scale = 4
    W, H = cell_w * scale, cell_h * scale
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    skin = (245, 205, 135)
    head_radius = int(min(W, H) * 0.22)
    center_x = W // 2
    head_y = int(H * 0.3)
    torso_w = int(W * 0.45)
    torso_h = int(H * 0.45)
    torso_x = center_x - torso_w // 2
    torso_y = head_y + int(head_radius * 0.5)
    pygame.draw.rect(surf, shirt, (torso_x, torso_y, torso_w, torso_h))
    pygame.draw.circle(surf, skin, (center_x, head_y), head_radius)
    return pygame.transform.scale(surf, (cell_w, cell_h)).convert_alpha()
