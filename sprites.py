import pygame
import random
import settings

_cell_w = settings.GRID_SCALE
_cell_h = settings.GRID_SCALE
_skin_color = (245, 205, 135)
_eye_color = (165, 42, 42)
_torso_width = 0.6
_torso_height = 0.5
_head_size = 0.34
_head_height = 0.3
_eye_distance = 0.3
_eye_height = 0.1
creature_surfaces = []

def _make_surface(shirt):
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
    pygame.draw.circle(surf, _skin_color, (cx, head_y), head_radius)
    eye_x_off = max(1, round(head_radius * _eye_distance))
    eye_y = int(head_y - head_radius * _eye_height)
    surf.set_at((cx - eye_x_off, eye_y), _eye_color)
    surf.set_at((cx + eye_x_off, eye_y), _eye_color)
    return surf.convert_alpha()

def bake_creature_surfaces(count):
    creature_surfaces.clear()
    creature_surfaces.extend(_make_surface((random.randint(80, 220), random.randint(80, 220), random.randint(80, 220))) for _ in range(count))

