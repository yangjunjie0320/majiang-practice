from app import hu
from app.tiles import counts_from_tiles


def c(*tiles):
    return counts_from_tiles(list(tiles))


def test_pinghu():
    counts = c("1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
               "1s", "1s", "1s", "2s", "2s")
    assert hu.is_win(counts)
    assert hu.fan(counts) == (1, ["平胡"])


def test_nine_gates_decomposition():
    # 1112345678999m + 9m：将=11，拆 123 456 789 999，需要正确的拆分搜索
    counts = c("1m", "1m", "1m", "2m", "3m", "4m", "5m", "6m", "7m",
               "8m", "9m", "9m", "9m", "9m")
    assert hu.is_win(counts)
    mult, patterns = hu.fan(counts)
    assert mult == 8 and set(patterns) == {"清一色", "根x1"}


def test_duidui():
    counts = c("1m", "1m", "1m", "3m", "3m", "3m", "7s", "7s", "7s",
               "9s", "9s", "9s", "5m", "5m")
    assert hu.is_win(counts)
    assert hu.fan(counts) == (2, ["对对胡"])


def test_qingyise():
    counts = c("1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
               "2m", "3m", "4m", "5m", "5m")
    assert hu.is_win(counts)
    assert hu.fan(counts) == (4, ["清一色"])


def test_qidui():
    counts = c("1m", "1m", "3m", "3m", "5m", "5m", "7m", "7m",
               "2s", "2s", "4s", "4s", "6s", "6s")
    assert hu.is_win(counts)
    assert hu.fan(counts) == (4, ["七对"])


def test_long_qidui():
    counts = c("1m", "1m", "1m", "1m", "3m", "3m", "5m", "5m",
               "2s", "2s", "4s", "4s", "6s", "6s")
    assert hu.is_win(counts)
    assert hu.fan(counts) == (8, ["龙七对"])


def test_qing_qidui():
    counts = c("1m", "1m", "2m", "2m", "3m", "3m", "4m", "4m",
               "5m", "5m", "6m", "6m", "7m", "7m")
    assert hu.fan(counts) == (16, ["七对", "清一色"])


def test_gen():
    # 2222m 作为 222 刻子 + 2 进顺子 234：平胡带一根 = 2 倍
    counts = c("2m", "2m", "2m", "2m", "3m", "4m", "5m", "6m", "7m",
               "1s", "1s", "1s", "9s", "9s")
    assert hu.is_win(counts)
    assert hu.fan(counts) == (2, ["根x1"])


def test_huazhu_cannot_win():
    # 三门齐 = 花猪，不能胡
    counts = c("1m", "2m", "3m", "4m", "5m", "6m", "7m", "8m", "9m",
               "1s", "1s", "1s", "2p", "2p")
    assert not hu.is_win(counts)


def test_not_win():
    counts = c("1m", "2m", "4m", "5m", "7m", "8m", "1s", "2s", "4s",
               "5s", "7s", "8s", "9s", "9s")
    assert not hu.is_win(counts)


def test_greedy_trap():
    # 万: 334455667788 + 99 将，多种拆法
    counts = c("3m", "3m", "4m", "4m", "5m", "5m", "6m", "6m",
               "7m", "7m", "8m", "8m", "9m", "9m")
    assert hu.is_win(counts)  # 345 345 678 678 99 或七对
