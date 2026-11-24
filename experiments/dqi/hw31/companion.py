"""Exact two-payload Bézout transform with leading-coefficient repair."""

import numpy as np


def multiply(x, y, tables):
    exponent = (tables.log[x] + tables.log[y]) % 4095
    return np.where((x != 0) & (y != 0), tables.antilog[exponent], 0).astype(np.uint16)


def inverse(x, tables):
    return np.where(x != 0, tables.antilog[(-tables.log[x]) % 4095], 0).astype(np.uint16)


def evaluate(words, point, tables):
    value = words[:, -1].copy()
    for coefficient in words[:, -2::-1].T:
        value = multiply(value, point, tables) ^ coefficient
    return value


def dot(words, values, tables):
    return np.bitwise_xor.reduce(multiply(words[:, :, None], values, tables), axis=1)


def geometry(f, g, tables, primary_point=1):
    stages = []
    while g.shape[1]:
        f, g = f.copy(), g.copy()
        n = g.shape[1]
        missing = g[:, -1] == 0
        assert np.all(np.any(g, axis=1))
        raise_by = np.argmax(g[:, ::-1] != 0, axis=1)
        point = np.full(len(f), primary_point, dtype=np.uint16)
        needs_point = missing & (evaluate(f, point, tables) == 0)
        for a in (a for a in range(1, 20) if a != primary_point):
            if not needs_point.any():
                break
            point[needs_point] = a
            needs_point &= evaluate(f, point, tables) == 0
        assert not needs_point.any()
        for j in range(int(raise_by.max())):
            affected = raise_by > j
            old = g[affected]
            assert not old[:, -1].any()
            g[affected] = multiply(old, point[affected, None], tables)
            g[affected, 1:] ^= old[:, :-1]
        divisor = g[:, -1]
        assert divisor.all()
        inv_divisor = inverse(divisor, tables)
        q1 = multiply(f[:, -1], inv_divisor, tables)
        stages.append((f, g, point, raise_by, q1))
        if n == 1:
            break
        q0 = multiply(f[:, -2] ^ multiply(q1, g[:, -2], tables), inv_divisor, tables)
        rem = f[:, :n-1] ^ multiply(q0[:, None], g[:, :n-1], tables)
        rem[:, 1:] ^= multiply(q1[:, None], g[:, :n-2], tables)
        f, g = g, rem
    return stages


def companion(f, point, values, tables, reverse):
    s_inverse = inverse(f[:, -1], tables)
    if not reverse:
        result = multiply(values, point[:, None, None], tables)
        result[:, :-1] ^= values[:, 1:]
        result[:, -1] ^= multiply(dot(f[:, :-1], values, tables), s_inverse[:, None], tables)
        return result

    p_inverse = inverse(point, tables)
    already = np.zeros_like(values)
    slopes = np.ones(f[:, :-1].shape, dtype=np.uint16)
    for j in range(values.shape[1] - 2, -1, -1):
        already[:, j] = multiply(values[:, j] ^ already[:, j+1], p_inverse[:, None], tables)
        slopes[:, j] = multiply(slopes[:, j+1], p_inverse, tables)
    denominator = point ^ multiply(dot(f[:, :-1], slopes[:, :, None], tables)[:, 0], s_inverse, tables)
    assert denominator.all()
    high = multiply(values[:, -1] ^ multiply(dot(f[:, :-1], already, tables), s_inverse[:, None], tables),
                    inverse(denominator, tables)[:, None], tables)
    return already ^ multiply(slopes[:, :, None], high[:, None, :], tables)


def compensate(f, point, raise_by, values, tables, reverse):
    for i in range(int(raise_by.max())):
        mask = raise_by > i
        values[mask] = companion(f[mask], point[mask], values[mask], tables, reverse)


def transform(stages, values, tables, solve, i=0):
    if i == len(stages):
        return values.copy()
    f, g, point, raised, q1 = stages[i]
    values = values.copy()
    inv_g = inverse(g[:, -1], tables)
    g_low = g[:, :-1]
    if solve:
        high = multiply(values[:, -1], inv_g[:, None], tables)
        low = values[:, :-1] ^ multiply(g_low[:, :, None], high[:, None, :], tables)
        low = transform(stages, low, tables, solve, i+1)
        high = multiply(high, inverse(q1, tables)[:, None], tables)
        high = multiply(high ^ dot(g_low, low, tables), inv_g[:, None], tables)
        result = np.concatenate((low, high[:, None, :]), axis=1)
        compensate(f, point, raised, result, tables, reverse=False)
        return result

    compensate(f, point, raised, values, tables, reverse=True)
    high = multiply(values[:, -1], g[:, -1, None], tables) ^ dot(g_low, values[:, :-1], tables)
    high = multiply(high, q1[:, None], tables)
    low = transform(stages, values[:, :-1], tables, solve, i+1)
    low ^= multiply(g_low[:, :, None], high[:, None, :], tables)
    high = multiply(high, g[:, -1, None], tables)
    return np.concatenate((low, high[:, None, :]), axis=1)
