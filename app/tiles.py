"""牌的表示与转换。

内部用字符串表示一张牌，如 "3m"：数字为点数 1-9，字母为花色
（m=万 s=条 p=筒）。计数表示为长度 27 的列表，下标 = 花色序号*9 + 点数-1。
川麻没有字牌。
"""

SUITS = "msp"
SUIT_NAMES = {"m": "万", "s": "条", "p": "筒"}

ALL_TILES = [f"{r}{s}" for s in SUITS for r in range(1, 10)]


def tile_index(tile: str) -> int:
    rank, suit = int(tile[0]), tile[1]
    return SUITS.index(suit) * 9 + (rank - 1)


def index_to_tile(i: int) -> str:
    return f"{i % 9 + 1}{SUITS[i // 9]}"


def format_tile(tile: str) -> str:
    return f"{tile[0]}{SUIT_NAMES[tile[1]]}"


def counts_from_tiles(tiles: list[str]) -> list[int]:
    counts = [0] * 27
    for t in tiles:
        counts[tile_index(t)] += 1
    return counts


def tiles_from_counts(counts: list[int]) -> list[str]:
    tiles = []
    for i, c in enumerate(counts):
        tiles.extend([index_to_tile(i)] * c)
    return tiles


def sort_tiles(tiles: list[str]) -> list[str]:
    return sorted(tiles, key=tile_index)


def suits_in(counts: list[int]) -> set[str]:
    return {SUITS[i // 9] for i, c in enumerate(counts) if c > 0}
