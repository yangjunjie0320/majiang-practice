from app.shanten import shanten, ukeire
from app.tiles import counts_from_tiles


def c(*tiles):
    return counts_from_tiles(list(tiles))


def test_complete_hand_is_minus_one():
    counts = c("1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
               "1s", "1s", "1s", "2s", "2s")
    assert shanten(counts) == -1


def test_tenpai_is_zero():
    counts = c("1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
               "1s", "1s", "1s", "2s")
    assert shanten(counts) == 0


def test_one_shanten():
    # 三副顺子 + 两个搭子 + 将，差一步下叫
    counts = c("1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m",
               "1s", "2s", "5s", "5s", "9s")
    assert shanten(counts) == 1


def test_seven_pairs_shanten():
    # 5 对 + 2 单张 = 1 向听（七对路线）
    counts = c("1m", "1m", "3m", "3m", "5m", "5m", "7m", "7m",
               "2s", "2s", "4s", "6s", "8s")
    assert shanten(counts) == 1


def test_missing_suit_tiles_are_dead():
    # 手里有定缺门的刻子也不能用
    counts = c("1p", "1p", "1p", "4m", "5m", "6m", "7m", "8m", "9m",
               "1s", "1s", "1s", "2s")
    assert shanten(counts, missing_suit=None) == 0
    assert shanten(counts, missing_suit="p") > 0


def test_ukeire_tenpai():
    counts = c("1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
               "1s", "1s", "1s", "2s")
    st, tiles, total = ukeire(counts, None)
    assert st == 0
    assert "2s" in tiles
    assert total >= 3  # 2s 还剩 3 张


def test_ukeire_excludes_missing_suit():
    counts = c("1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m",
               "1s", "2s", "5s", "5s", "9p")
    st, tiles, total = ukeire(counts, "p")
    assert all(not t.endswith("p") for t in tiles)
