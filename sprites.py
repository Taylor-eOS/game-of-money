import pygame
import random
import settings

_surface_cache = {}
_cell_w = settings.SCALE
_cell_h = settings.SCALE

def random_shirt_color():
    return (random.randint(80, 220), random.randint(80, 220), random.randint(80, 220))

def create_creature_surface(shirt=(170, 70, 70), dead=False):
    key = (shirt, dead)
    if key in _surface_cache:
        return _surface_cache[key]
    scale = 4
    W, H = _cell_w * scale, _cell_h * scale
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
    if dead:
        surf = pygame.transform.rotate(surf, 70)
    result = pygame.transform.scale(surf, (_cell_w, _cell_h)).convert_alpha()
    _surface_cache[key] = result
    return result

def bake_creature_surfaces(shirt_list):
    return [create_creature_surface(shirt) for shirt in shirt_list]
