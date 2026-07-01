import numpy as np
import features

NET_IN = features.feature_count()
NET_H = 64
NET_OUT = 1
W1_SIZE = NET_IN * NET_H
B1_SIZE = NET_H
W2_SIZE = NET_H * NET_OUT
B2_SIZE = NET_OUT
TRAIT_DIM = W1_SIZE + B1_SIZE + W2_SIZE + B2_SIZE

def xavier_layer(fan_in, fan_out, rng=None):
    limit = np.sqrt(6.0 / (fan_in + fan_out))
    if rng is not None:
        return rng.uniform(-limit, limit, size=fan_in * fan_out).astype(np.float32)
    return np.random.uniform(-limit, limit, size=fan_in * fan_out).astype(np.float32)

def init_traits(rng=None):
    w1 = xavier_layer(NET_IN, NET_H, rng)
    b1 = np.zeros(NET_H, dtype=np.float32)
    w2 = xavier_layer(NET_H, NET_OUT, rng)
    b2 = np.zeros(NET_OUT, dtype=np.float32)
    return np.concatenate([w1, b1, w2, b2])

def unpack_weights(traits):
    w1 = traits[:W1_SIZE].reshape(NET_IN, NET_H)
    b1 = traits[W1_SIZE:W1_SIZE + B1_SIZE]
    w2 = traits[W1_SIZE + B1_SIZE:W1_SIZE + B1_SIZE + W2_SIZE].reshape(NET_H, NET_OUT)
    b2 = traits[W1_SIZE + B1_SIZE + W2_SIZE:]
    return w1, b1, w2, b2

def net_forward(traits, features):
    w1, b1, w2, b2 = unpack_weights(traits)
    h = features @ w1 + b1
    h = np.where(h > 0, h, 0.01 * h)
    return float((h @ w2 + b2)[0])

def mutate_traits(traits, std):
    mask = np.random.random(traits.shape) < 0.15
    noise = np.random.normal(0.0, std, size=traits.shape).astype(np.float32)
    return np.clip(traits + noise * mask, -8.0, 8.0)
