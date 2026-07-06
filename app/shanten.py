"""向听数与进张计算。

向听数 = 距离下叫（听牌）还差几步；0 = 已下叫，-1 = 已胡。
定缺花色的牌不能参与成牌，计算前需将其从计数中剔除。
"""

from .tiles import SUITS, index_to_tile


def _seven_pairs_shanten(counts: list[int]) -> int:
    pairs = sum(1 for c in counts if c >= 2)
    kinds = sum(1 for c in counts if c >= 1)
    return 6 - pairs + max(0, 7 - kinds)


def _standard_shanten(counts: list[int]) -> int:
    """4 面子 + 1 将的向听数，经典回溯：枚举面子/搭子拆分取最优。"""
    counts = counts[:]
    best = [8]

    def evaluate(melds: int, partials: int, has_pair: bool) -> None:
        if melds + partials > 4:
            partials = 4 - melds
        st = 8 - 2 * melds - partials - (1 if has_pair else 0)
        best[0] = min(best[0], st)

    def walk(i: int, melds: int, partials: int, has_pair: bool) -> None:
        while i < 27 and counts[i] == 0:
            i += 1
        if i == 27:
            evaluate(melds, partials, has_pair)
            return
        suit_end = (i // 9 + 1) * 9
        # 刻子
        if counts[i] >= 3:
            counts[i] -= 3
            walk(i, melds + 1, partials, has_pair)
            counts[i] += 3
        # 顺子
        if i + 2 < suit_end and counts[i + 1] > 0 and counts[i + 2] > 0:
            counts[i] -= 1
            counts[i + 1] -= 1
            counts[i + 2] -= 1
            walk(i, melds + 1, partials, has_pair)
            counts[i] += 1
            counts[i + 1] += 1
            counts[i + 2] += 1
        # 对子：优先做将，其次做刻子搭子
        if counts[i] >= 2:
            counts[i] -= 2
            if not has_pair:
                walk(i, melds, partials, True)
            walk(i, melds, partials + 1, has_pair)
            counts[i] += 2
        # 两面/坎张搭子
        if i + 1 < suit_end and counts[i + 1] > 0:
            counts[i] -= 1
            counts[i + 1] -= 1
            walk(i, melds, partials + 1, has_pair)
            counts[i] += 1
            counts[i + 1] += 1
        if i + 2 < suit_end and counts[i + 2] > 0:
            counts[i] -= 1
            counts[i + 2] -= 1
            walk(i, melds, partials + 1, has_pair)
            counts[i] += 1
            counts[i + 2] += 1
        # 单张跳过
        counts[i] -= 1
        walk(i, melds, partials, has_pair)
        counts[i] += 1

    walk(0, 0, 0, False)
    return best[0]


def shanten(counts: list[int], missing_suit: str | None = None) -> int:
    """向听数，missing_suit 为定缺花色（其牌视为废牌）。"""
    counts = counts[:]
    if missing_suit is not None:
        base = SUITS.index(missing_suit) * 9
        for i in range(base, base + 9):
            counts[i] = 0
    return min(_standard_shanten(counts), _seven_pairs_shanten(counts))


def ukeire(counts: list[int], missing_suit: str | None) -> tuple[int, list[str], int]:
    """13 张手牌的进张：返回 (当前向听, 进张牌列表, 进张总枚数)。

    进张 = 摸到后向听数下降的牌；枚数按 4 - 手中已有张数计。
    """
    base_shanten = shanten(counts, missing_suit)
    tiles = []
    total = 0
    for i in range(27):
        if missing_suit is not None and SUITS[i // 9] == missing_suit:
            continue
        if counts[i] >= 4:
            continue
        counts[i] += 1
        if shanten(counts, missing_suit) < base_shanten:
            tiles.append(index_to_tile(i))
            total += 4 - (counts[i] - 1)
        counts[i] -= 1
    return base_shanten, tiles, total
