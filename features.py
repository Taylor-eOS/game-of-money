import numpy as np
import settings

FEATURE_REGISTRY = []
FEATURE_NAMES = []

def register_feature(name):
    def wrap(fn):
        FEATURE_REGISTRY.append(fn)
        FEATURE_NAMES.append(name)
        return fn
    return wrap

def feature_count():
    return len(FEATURE_REGISTRY)

def _ctx(creature_state, ci, tx, ty, object_type):
    cx, cy = int(creature_state.x[ci]), int(creature_state.y[ci])
    manhattan = abs(tx - cx) + abs(ty - cy)
    alive_mask = creature_state.alive
    alive_x = creature_state.x[alive_mask]
    alive_y = creature_state.y[alive_mask]
    return {
        "ci": ci,
        "cx": cx,
        "cy": cy,
        "tx": tx,
        "ty": ty,
        "manhattan": manhattan,
        "alive_mask": alive_mask,
        "alive_x": alive_x,
        "alive_y": alive_y,
        "object_type": object_type,
        "creature_state": creature_state,
    }

@register_feature("dx")
def _f_dx(ctx):
    return float(ctx["tx"] - ctx["cx"]) / max(settings.GRID_COLS, settings.GRID_ROWS)

@register_feature("dy")
def _f_dy(ctx):
    return float(ctx["ty"] - ctx["cy"]) / max(settings.GRID_COLS, settings.GRID_ROWS)

@register_feature("dist")
def _f_dist(ctx):
    return np.log1p(float(ctx["manhattan"])) / np.log1p(settings.GRID_COLS + settings.GRID_ROWS)

@register_feature("density")
def _f_density(ctx):
    r = settings.DENSITY_RADIUS
    tx, ty = ctx["tx"], ctx["ty"]
    return float(np.sum((np.abs(ctx["alive_x"] - tx) + np.abs(ctx["alive_y"] - ty)) <= r)) / settings.DENSITY_NORM

@register_feature("closer_count")
def _f_closer_count(ctx):
    tx, ty = ctx["tx"], ctx["ty"]
    closer = np.sum((np.abs(ctx["alive_x"] - tx) + np.abs(ctx["alive_y"] - ty)) < ctx["manhattan"])
    return float(closer) / max(1.0, float(np.sum(ctx["alive_mask"])))

@register_feature("hp_norm")
def _f_hp_norm(ctx):
    return float(ctx["creature_state"].hp[ctx["ci"]]) / 100.0

@register_feature("is_gold")
def _f_is_gold(ctx):
    return 1.0 if ctx["object_type"] == "gold" else 0.0

@register_feature("own_gold_norm")
def _f_own_gold_norm(ctx):
    own_gold = float(ctx["creature_state"].gold[ctx["ci"]])
    return np.log1p(own_gold) / np.log1p(50.0)

@register_feature("rank_norm")
def _f_rank_norm(ctx):
    creature_state = ctx["creature_state"]
    own_gold = float(creature_state.gold[ctx["ci"]])
    alive_indices = np.where(ctx["alive_mask"])[0]
    gold_vals = creature_state.gold[alive_indices].astype(np.float32)
    return float(np.sum(gold_vals < own_gold)) / max(1.0, float(len(alive_indices) - 1))

@register_feature("bias")
def _f_bias(ctx):
    return 1.0

@register_feature("own_x_norm")
def _f_own_x_norm(ctx):
    return float(ctx["cx"]) / max(1, settings.GRID_COLS - 1)

@register_feature("own_y_norm")
def _f_own_y_norm(ctx):
    return float(ctx["cy"]) / max(1, settings.GRID_ROWS - 1)

def build_features(creature_state, ci, tx, ty, object_type):
    ctx = _ctx(creature_state, ci, tx, ty, object_type)
    values = [fn(ctx) for fn in FEATURE_REGISTRY]
    return np.array(values, dtype=np.float32)
