import numpy as np

NET_IN = 8
NET_H = 64
NET_OUT = 1
W1_SIZE = NET_IN * NET_H
B1_SIZE = NET_H
W2_SIZE = NET_H * NET_OUT
B2_SIZE = NET_OUT
TRAIT_DIM = W1_SIZE + B1_SIZE + W2_SIZE + B2_SIZE

HEBBIAN_CLIP = 5.0

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
    h = np.tanh(features @ w1 + b1)
    return float((h @ w2 + b2)[0]), h

def apply_hebbian(traits, feats, hidden, lr):
    if feats is None or hidden is None:
        return
    dw1 = np.outer(feats, hidden) * lr
    db1 = hidden * lr
    dw2 = np.outer(hidden, np.array([1.0], dtype=np.float32)) * lr
    db2 = np.array([lr], dtype=np.float32)
    traits[:W1_SIZE] = np.clip(traits[:W1_SIZE] + dw1.ravel(), -HEBBIAN_CLIP, HEBBIAN_CLIP)
    traits[W1_SIZE:W1_SIZE + B1_SIZE] = np.clip(traits[W1_SIZE:W1_SIZE + B1_SIZE] + db1, -HEBBIAN_CLIP, HEBBIAN_CLIP)
    w2_start = W1_SIZE + B1_SIZE
    traits[w2_start:w2_start + W2_SIZE] = np.clip(traits[w2_start:w2_start + W2_SIZE] + dw2.ravel(), -HEBBIAN_CLIP, HEBBIAN_CLIP)
    traits[w2_start + W2_SIZE:] = np.clip(traits[w2_start + W2_SIZE:] + db2, -HEBBIAN_CLIP, HEBBIAN_CLIP)
