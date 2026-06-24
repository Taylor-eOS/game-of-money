import pygame
import random

def random_shirt_color():
    return (random.randint(80, 220), random.randint(80, 220), random.randint(80, 220))

def create_creature_surface(cell_w, cell_h, shirt=(170, 70, 70)):
    scale = 4
    W, H = cell_w * scale, cell_h * scale
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    skin = (245, 205, 135)
    dark = (35, 25, 15)
    head_w = int(W * 0.55)
    head_h = int(H * 0.35)
    hcx = W // 2
    hcy = int(H * 0.25)
    torso_w = int(W * 0.65)
    torso_h = int(H * 0.45)
    torso_x = hcx - torso_w // 2
    torso_y = hcy + int(head_h * 0.30)
    pygame.draw.ellipse(surf, shirt, (torso_x, torso_y, torso_w, torso_h))
    pygame.draw.rect(surf, skin, (hcx - head_w // 2, hcy - head_h // 2, head_w, head_h // 2))
    pygame.draw.ellipse(surf, skin, (hcx - head_w // 2, hcy - head_h // 2, head_w, head_h))
    eye_y = hcy - int(head_h * 0.05)
    pygame.draw.rect(surf, dark, (hcx - int(head_w * 0.22), eye_y, 2, 2))
    pygame.draw.rect(surf, dark, (hcx + int(head_w * 0.22) - 2, eye_y, 2, 2))
    return pygame.transform.scale(surf, (cell_w, cell_h)).convert_alpha()
