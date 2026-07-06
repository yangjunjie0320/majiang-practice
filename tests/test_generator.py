import random

from fastapi.testclient import TestClient

from app import hu
from app.generator import make_discard_problem, make_ting_problem
from app.main import app
from app.shanten import shanten
from app.tiles import counts_from_tiles, suits_in, tile_index


def test_ting_problem_valid():
    rng = random.Random(42)
    for _ in range(20):
        p = make_ting_problem(rng)
        assert len(p["hand"]) == 13
        counts = counts_from_tiles(p["hand"])
        assert len(suits_in(counts)) <= 2
        assert p["answer"]["hu_tiles"]
        for h in p["answer"]["hu_tiles"]:
            counts[tile_index(h["tile"])] += 1
            assert hu.is_win(counts)
            assert h["fan"] >= 1
            counts[tile_index(h["tile"])] -= 1


def test_discard_problem_valid():
    rng = random.Random(7)
    for _ in range(5):
        p = make_discard_problem(rng)
        assert len(p["hand"]) == 14
        assert p["answer"]["best"]
        assert set(p["answer"]["best"]) <= set(p["hand"])
        # 手牌只含定缺外的两门（清一色路线可能只剩一门）
        assert all(not t.endswith(p["missing_suit"]) for t in p["hand"])
        assert len(suits_in(counts_from_tiles(p["hand"]))) <= 2
        # 每个答案都必须是打完即下叫，且听牌可核验：加上任一听牌即胡
        counts = counts_from_tiles(p["hand"])
        for d in p["answer"]["detail"]:
            assert d["count"] > 0
            counts[tile_index(d["tile"])] -= 1
            assert shanten(counts, p["missing_suit"]) == 0
            for w in d["waits"]:
                counts[tile_index(w)] += 1
                assert hu.is_win(counts)
                counts[tile_index(w)] -= 1
            counts[tile_index(d["tile"])] += 1


def test_api():
    client = TestClient(app)
    for mode in ("ting", "discard"):
        resp = client.get(f"/api/problem/{mode}")
        assert resp.status_code == 200
        assert resp.json()["mode"] == mode
    assert client.get("/api/problem/bogus").status_code == 404
    assert client.get("/").status_code == 200
