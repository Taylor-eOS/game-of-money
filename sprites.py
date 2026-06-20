import pygame
import random

def random_shirt_color():
    return (random.randint(80, 220), random.randint(80, 220), random.randint(80, 220))

def create_creature_surfaces(CELL_W, CELL_H, shirt=(170, 70, 70)):
    scale = 4
    W, H = CELL_W * scale, CELL_H * scale
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
    return pygame.transform.scale(surf, (CELL_W, CELL_H)).convert_alpha()

def build_blit_list(CELL_W, CELL_H, creature_x, creature_y):
    return [[create_creature_surfaces(CELL_W, CELL_H, random_shirt_color()),
             pygame.Rect(int(creature_x[i]) * CELL_W,
                         int(creature_y[i]) * CELL_H,
                         CELL_W, CELL_H)]
            for i in range(len(creature_x))]
