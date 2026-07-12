#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线枚举全部题形并按格抽样，生成题库 assets/pools.js。

用法：uv run --with numpy python scripts/gen_pools.py

题库结构：按（模式, 副露数 m, 胡法数量 n）分格，每格从枚举全集随机保留
最多 100 个暗牌形（固定种子可复现），不足 100 的全收。格键如 t_0_1
（听牌、门清、听 1 种）、d_2_5（下叫、2 组副露、5 种打法）。
运行时由 majiang.js 按 难度→n→m 权重抽格、洗牌袋抽形、置换花色配副露。

构造（固定 万/条 两门）：W_m = (4-m) 组(顺/刻)+将 的和牌集（m=0 含七对）；
听牌手 = W_m 去一张去重，n = 听几种；下叫手 = 听牌手加一张且非胡去重，
n = 几种下叫打法。编码 base-5（下标 = 花色*9+点数-1），
每格排序后差分 varint 再 base64。
副露对答案的封顶影响由运行时配副露后重算校验，池按暗牌形枚举。
"""
import base64
import time
from itertools import combinations_with_replacement
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
P5 = [5 ** i for i in range(19)]
CAP = 100
SEED = 20260712

# 各格全集大小（本仓库枚举结论，防回归）
EXPECT = {
    "t": {
        0: {1: 2528748, 2: 1191910, 3: 273554, 4: 51746, 5: 13110,
            6: 1744, 7: 222, 8: 96, 9: 2},
        1: {1: 152838, 2: 140697, 3: 21904, 4: 3544, 5: 810, 6: 60, 7: 4, 8: 4},
        2: {1: 13288, 2: 10594, 3: 1150, 4: 128, 5: 22},
        3: {1: 720, 2: 393, 3: 24},
        4: {1: 18},
    },
    "d": {
        0: {1: 17733720, 2: 16734728, 3: 2698514, 4: 701898, 5: 317796,
            6: 154647, 7: 12374, 8: 518},
        1: {1: 2307710, 2: 942302, 3: 190728, 4: 59934, 5: 32054, 6: 1788, 7: 56},
        2: {1: 180350, 2: 84755, 3: 13694, 4: 5304, 5: 184, 6: 4},
        3: {1: 6902, 2: 4884, 3: 726, 4: 10},
        4: {2: 153},
    },
}


def digit(arr, i):
    return (arr // P5[i]) % 5


def member(sorted_arr, vals):
    idx = np.searchsorted(sorted_arr, vals)
    idx_c = np.minimum(idx, len(sorted_arr) - 1)
    return (idx < len(sorted_arr)) & (sorted_arr[idx_c] == vals)


def build_wins(m):
    sets = []
    for b in (0, 9):
        for r in range(7):
            v = [0] * 18
            v[b + r] = v[b + r + 1] = v[b + r + 2] = 1
            sets.append(v)
        for r in range(9):
            v = [0] * 18
            v[b + r] = 3
            sets.append(v)
    wins = set()
    for combo in combinations_with_replacement(sets, 4 - m):
        base = [0] * 18
        for t in combo:
            for i in range(18):
                base[i] += t[i]
        if max(base) > 4:
            continue
        e0 = sum(base[i] * P5[i] for i in range(18))
        for i in range(18):
            if base[i] <= 2:
                wins.add(e0 + 2 * P5[i])
    if m == 0:  # 七对（4 张算 2 对），仅门清
        def rec(pos, left, enc):
            if left == 0:
                wins.add(enc)
                return
            if pos == 18:
                return
            rec(pos + 1, left, enc)
            rec(pos + 1, left - 1, enc + 2 * P5[pos])
            if left >= 2:
                rec(pos + 1, left - 2, enc + 4 * P5[pos])
        rec(0, 7, 0)
    arr = np.fromiter(wins, dtype=np.int64, count=len(wins))
    arr.sort()
    return arr


def varint(arr):
    buf = bytearray()
    prev = 0
    for x in arr:
        d = int(x) - prev
        prev = int(x)
        while d >= 128:
            buf.append((d & 127) | 128)
            d >>= 7
        buf.append(d)
    return bytes(buf)


t0 = time.time()
rng = np.random.default_rng(SEED)
cells = {}
for m in range(5):
    W = build_wins(m)
    T = np.unique(np.concatenate([W[digit(W, i) > 0] - P5[i] for i in range(18)]))
    waits = np.zeros(len(T), dtype=np.int8)
    for i in range(18):
        ok = digit(T, i) <= 3
        waits[ok] += member(W, T[ok] + P5[i])
    D = np.unique(np.concatenate([T[digit(T, i) <= 3] + P5[i] for i in range(18)]))
    D = D[~member(W, D)]
    opts = np.zeros(len(D), dtype=np.int8)
    for i in range(18):
        ok = digit(D, i) > 0
        opts[ok] += member(T, D[ok] - P5[i])
    for mode, arr, cnt in (("t", T, waits), ("d", D, opts)):
        dist = np.bincount(cnt, minlength=10)
        assert {n: int(c) for n, c in enumerate(dist) if c and n > 0} \
            == EXPECT[mode][m], (mode, m, dist)
        for n, total in EXPECT[mode][m].items():
            cell = arr[cnt == n]
            if len(cell) > CAP:
                cell = np.sort(rng.choice(cell, CAP, replace=False))
            cells[f"{mode}_{m}_{n}"] = cell
    print(f"m={m} 枚举完成 [{time.time()-t0:.1f}s]", flush=True)

n_t = sum(len(v) for k, v in cells.items() if k[0] == "t")
n_d = sum(len(v) for k, v in cells.items() if k[0] == "d")
print(f"题库：听牌 {n_t} 形 / 下叫 {n_d} 形，共 {len(cells)} 格")
assert (n_t, n_d) == (2030, 2370), (n_t, n_d)

lines = [
    "/* 由 scripts/gen_pools.py 生成，勿手改。",
    " * 题库：每格 = (模式 t/d, 副露数, 胡法数量) 的暗牌形样本（<=100，",
    " * 固定 万/条 两门），base-5 编码排序后差分 varint 再 base64，",
    " * 解码与抽题在 majiang.js。 */",
    "var MajiangPools = {",
]
for k in sorted(cells):
    b64 = base64.b64encode(varint(cells[k])).decode()
    lines.append(f'  {k}:\n"{b64}",')
lines.append("};")
lines.append('if (typeof module !== "undefined") module.exports = MajiangPools;')
out = ROOT / "assets" / "pools.js"
out.write_text("\n".join(lines) + "\n")
print(f"written {out} {out.stat().st_size} bytes [{time.time()-t0:.1f}s]")
