#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线枚举副露困难题池，生成 assets/pools.js。

用法：uv run --with numpy python scripts/gen_pools.py

池内容（固定 万/条 两门存储，运行时随机置换花色、配副露并重校验档位）：
- ting1/ting2：1/2 组副露的听牌困难题暗牌形（13-3m 张、听 >=4 种牌）
- discard1/discard2：下叫困难题暗牌形（14-3m 张、非胡、>=5 种下叫打法）

构造：W_m = (4-m) 组(顺/刻)+将 的两门和牌集（副露后暗牌不含七对）；
听牌手 = W_m 去一张去重；下叫手 = 听牌手加一张且非胡去重。
编码 base-5（下标 = 花色*9 + 点数-1），排序后差分 varint 再 base64。
副露对听牌枚数的封顶影响由运行时配副露后重算校验，池按暗牌形枚举。
"""
import base64
from itertools import combinations_with_replacement
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
P5 = [5 ** i for i in range(19)]
EXPECT = {"ting1": 4_422, "ting2": 150, "discard1": 33_898, "discard2": 188}
THRESH = {"ting": 4, "discard": 5}  # 困难档下限（见 DESIGN.md 难度分档）


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


pools = {}
for m in (1, 2):
    W = build_wins(m)
    T = np.unique(np.concatenate([W[digit(W, i) > 0] - P5[i] for i in range(18)]))
    waits = np.zeros(len(T), dtype=np.int8)
    for i in range(18):
        ok = digit(T, i) <= 3
        waits[ok] += member(W, T[ok] + P5[i])
    pools[f"ting{m}"] = T[waits >= THRESH["ting"]]
    D = np.unique(np.concatenate([T[digit(T, i) <= 3] + P5[i] for i in range(18)]))
    D = D[~member(W, D)]
    opts = np.zeros(len(D), dtype=np.int8)
    for i in range(18):
        ok = digit(D, i) > 0
        opts[ok] += member(T, D[ok] - P5[i])
    pools[f"discard{m}"] = D[opts >= THRESH["discard"]]

for k, v in pools.items():
    assert len(v) == EXPECT[k], (k, len(v), EXPECT[k])
    print(k, len(v))

lines = [
    "/* 由 scripts/gen_pools.py 生成，勿手改。",
    " * 副露困难题池：1/2 组副露的听牌(ting)/下叫(discard)困难题暗牌形，",
    " * 固定 万/条 两门，base-5 编码排序后差分 varint 再 base64，解码在 majiang.js。 */",
    "var MajiangPools = {",
]
for k in ("ting1", "ting2", "discard1", "discard2"):
    b64 = base64.b64encode(varint(pools[k])).decode()
    lines.append(f'  {k}:\n"{b64}",')
lines.append("};")
lines.append('if (typeof module !== "undefined") module.exports = MajiangPools;')
out = ROOT / "assets" / "pools.js"
out.write_text("\n".join(lines) + "\n")
print("written", out, out.stat().st_size, "bytes")
