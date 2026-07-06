"""练习题生成（逆向法：从完整胡牌出发构造题目）。

模式 ting：生成完整胡牌，枚举去掉一张的所有方式，取听牌数最多
（最难）的一种作为 13 张手牌，答案是所有能胡的牌及倍数。
模式 discard：生成完整胡牌，去掉一张、补一张随机牌，得到打对
一张即可下叫的 14 张手牌，答案是所有能下叫的打法及各自听的牌。
"""

import random

from . import hu, shanten
from .tiles import (
    SUITS,
    index_to_tile,
    sort_tiles,
    tile_index,
    tiles_from_counts,
)


def _random_complete_hand(
    rng: random.Random, suits: list[int] | None = None
) -> list[int] | None:
    """生成一副缺一门的 14 张胡牌计数，失败返回 None。"""
    suits = suits or rng.sample(range(3), 2)
    counts = [0] * 27

    def add(idx: int, n: int) -> bool:
        if counts[idx] + n > 4:
            return False
        counts[idx] += n
        return True

    if rng.random() < 0.25:
        # 七对：偶尔用同牌 4 张凑成龙七对
        need = 7
        while need > 0:
            idx = rng.choice(suits) * 9 + rng.randrange(9)
            take = 2 if need == 1 or rng.random() < 0.8 else 4
            take = min(take, need * 2)
            if add(idx, take):
                need -= take // 2
        return counts

    # 4 面子 + 1 将
    pair_idx = rng.choice(suits) * 9 + rng.randrange(9)
    if not add(pair_idx, 2):
        return None
    for _ in range(4):
        s = rng.choice(suits)
        if rng.random() < 0.5:
            start = s * 9 + rng.randrange(7)
            ok = add(start, 1) and add(start + 1, 1) and add(start + 2, 1)
        else:
            ok = add(s * 9 + rng.randrange(9), 3)
        if not ok:
            return None
    return counts


def _hu_tiles(counts: list[int]) -> list[dict]:
    """13 张手牌能胡的所有牌及倍数。"""
    hand_suits = sorted({i // 9 for i, c in enumerate(counts) if c > 0})
    result = []
    for s in hand_suits:
        for i in range(s * 9, s * 9 + 9):
            if counts[i] >= 4:
                continue
            counts[i] += 1
            if hu.is_win(counts):
                mult, patterns = hu.fan(counts)
                result.append(
                    {"tile": index_to_tile(i), "fan": mult, "patterns": patterns}
                )
            counts[i] -= 1
    return result


def make_ting_problem(rng: random.Random | None = None) -> dict:
    rng = rng or random.Random()
    while True:
        counts = _random_complete_hand(rng)
        if counts is None or not hu.is_win(counts):
            continue
        # 枚举去掉一张的所有方式，取听牌数最多（最难）的一种
        variants = []
        for removed in [i for i in range(27) if counts[i] > 0]:
            counts[removed] -= 1
            hu_tiles = _hu_tiles(counts)
            counts[removed] += 1
            if hu_tiles:
                variants.append((len(hu_tiles), removed, hu_tiles))
        if not variants:
            continue
        most = max(v[0] for v in variants)
        _, removed, hu_tiles = rng.choice([v for v in variants if v[0] == most])
        counts[removed] -= 1

        hand_suits = sorted({i // 9 for i, c in enumerate(counts) if c > 0})
        candidates = [index_to_tile(i) for s in hand_suits for i in range(s * 9, s * 9 + 9)]
        return {
            "mode": "ting",
            "hand": sort_tiles(tiles_from_counts(counts)),
            "candidates": candidates,
            "answer": {"hu_tiles": hu_tiles},
        }


def make_discard_problem(rng: random.Random | None = None) -> dict:
    rng = rng or random.Random()
    while True:
        # 定缺牌实战中会最先打光，手牌只从保留的两门生成才有练习价值
        kept = rng.sample(range(3), 2)
        missing_suit = SUITS[({0, 1, 2} - set(kept)).pop()]
        counts = _random_complete_hand(rng, suits=kept)
        if counts is None or not hu.is_win(counts):
            continue
        # 去掉一张、补一张随机牌：必然存在打完即下叫的选择
        counts[tile_index(rng.choice(tiles_from_counts(counts)))] -= 1
        while True:
            i = rng.choice(kept) * 9 + rng.randrange(9)
            if counts[i] < 4:
                counts[i] += 1
                break
        if hu.is_win(counts):
            continue

        # 找出所有打完即下叫的打法，及各自听的牌
        ting_options = []
        for i in range(27):
            if counts[i] == 0:
                continue
            counts[i] -= 1
            st, waits, total = shanten.ukeire(counts, missing_suit)
            counts[i] += 1
            # total==0 是形式听牌（听的牌全在自己手里），不算有效下叫
            if st == 0 and total > 0:
                ting_options.append(
                    {"tile": index_to_tile(i), "waits": waits, "count": total}
                )
        if not ting_options:
            continue
        ting_options.sort(key=lambda d: -d["count"])
        return {
            "mode": "discard",
            "hand": sort_tiles(tiles_from_counts(counts)),
            "missing_suit": missing_suit,
            "answer": {
                "best": [d["tile"] for d in ting_options],
                "detail": ting_options,
            },
        }
