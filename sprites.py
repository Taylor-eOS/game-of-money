import pygame
import numpy as np
import random
import settings

_cell_w = settings.GRID_SCALE
_cell_h = settings.GRID_SCALE
_skin_color_base = (245, 205, 135)
_skin_variation = 18
_eye_color = (165, 42, 42)
_torso_width = 0.6
_torso_height = 0.5
_head_size = 0.34
_head_height = 0.3
_eye_distance = 0.3
_eye_height = 0.1
_shirt_colors = np.empty((0, 3), dtype=np.uint8)
_death_angle_from = 40
_death_angle_to = 100
creature_surfaces = []
dead_surfaces = []

def _make_surface(shirt, skin_color):
    W, H = _cell_w, _cell_h
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    head_radius = max(1, int(min(W, H) * _head_size))
    head_y = int(H * _head_height)
    torso_w = int(W * _torso_width)
    if torso_w % 2 != W % 2:
        torso_w -= 1
    torso_x = cx - torso_w // 2
    torso_y = head_y + head_radius // 2
    torso_h = int(H * _torso_height)
    pygame.draw.rect(surf, shirt, (torso_x, int(torso_y), torso_w, torso_h))
    pygame.draw.circle(surf, skin_color, (cx, head_y), head_radius)
    eye_x_off = max(1, round(head_radius * _eye_distance))
    eye_y = int(head_y - head_radius * _eye_height)
    surf.set_at((cx - eye_x_off, eye_y), _eye_color)
    surf.set_at((cx + eye_x_off, eye_y), _eye_color)
    return surf.convert_alpha()

def bake_creature_surfaces(count):
    global _shirt_colors
    creature_surfaces.clear()
    dead_surfaces.clear()
    _shirt_colors = np.array([(random.randint(80, 220), random.randint(80, 220), random.randint(80, 220)) for _ in range(count)], dtype=np.uint8,)
    for i in range(count):
        shirt = tuple(int(c) for c in _shirt_colors[i])
        skin_v = random.randint(-_skin_variation, _skin_variation)
        skin_color = tuple(max(0, min(255, c + skin_v)) for c in _skin_color_base)
        alive_surf = _make_surface(shirt, skin_color)
        creature_surfaces.append(alive_surf)
        angle = random.randint(_death_angle_from, _death_angle_to) * random.choice([1, -1])
        dead_surfaces.append(pygame.transform.rotate(alive_surf, angle).convert_alpha())

