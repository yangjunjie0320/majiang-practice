"""胡牌判定与倍数计算。

第一版只考虑门清手牌（不含碰、杠等副露），倍数不含自摸、杠上花、
天地胡等情形。倍数表见 DESIGN.md。
"""

from .tiles import suits_in


def _suit_can_form_melds(block: list[int]) -> bool:
    """判断 9 张位的计数能否全部拆成刻子和顺子。

    贪心（先刻后顺）会漏掉如 [3,4,5,2,1] = 123x3+234+345 的拆法，
    必须回溯。
    """
    block = block[:]

    def walk(i: int) -> bool:
        while i < 9 and block[i] == 0:
            i += 1
        if i == 9:
            return True
        if block[i] >= 3:
            block[i] -= 3
            if walk(i):
                return True
            block[i] += 3
        if i <= 6 and block[i + 1] > 0 and block[i + 2] > 0:
            block[i] -= 1
            block[i + 1] -= 1
            block[i + 2] -= 1
            if walk(i):
                return True
            block[i] += 1
            block[i + 1] += 1
            block[i + 2] += 1
        return False

    return walk(0)


def _is_standard_win(counts: list[int]) -> bool:
    """4 副刻子/顺子 + 1 对将。"""
    for p in range(27):
        if counts[p] >= 2:
            counts[p] -= 2
            ok = all(
                sum(counts[s * 9:(s + 1) * 9]) % 3 == 0
                and _suit_can_form_melds(counts[s * 9:(s + 1) * 9])
                for s in range(3)
            )
            counts[p] += 2
            if ok:
                return True
    return False


def _is_seven_pairs(counts: list[int]) -> bool:
    return all(c % 2 == 0 for c in counts) and sum(c // 2 for c in counts) == 7


def _is_all_triplets(counts: list[int]) -> bool:
    """对对胡：存在一个将对，其余全是刻子。"""
    for p in range(27):
        if counts[p] == 2:
            return all(c in (0, 3) for i, c in enumerate(counts) if i != p)
    return False


def is_win(counts: list[int]) -> bool:
    """14 张牌是否胡牌（要求缺一门，花猪不能胡）。"""
    if sum(counts) != 14 or len(suits_in(counts)) > 2:
        return False
    return _is_seven_pairs(counts) or _is_standard_win(counts)


def fan(counts: list[int]) -> tuple[int, list[str]]:
    """计算 14 张胡牌的倍数和番型列表。

    倍数为乘法模型：七对x4 / 对对胡x2，清一色x4，每根x2。
    """
    assert is_win(counts)
    mult = 1
    patterns = []
    gen = sum(1 for c in counts if c == 4)
    if _is_seven_pairs(counts):
        # 龙七对 = 七对 + 根，根的倍数并入名称，不再单独列出
        patterns.append("龙七对" if gen > 0 else "七对")
        mult *= 4 * 2 ** gen
        gen = 0
    elif _is_all_triplets(counts):
        patterns.append("对对胡")
        mult *= 2
    if len(suits_in(counts)) == 1:
        patterns.append("清一色")
        mult *= 4
    if gen > 0:
        patterns.append(f"根x{gen}")
        mult *= 2 ** gen
    if not patterns:
        patterns.append("平胡")
    return mult, patterns
