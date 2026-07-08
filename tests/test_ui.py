"""index.html UI 流程测试（file:// 协议，无服务器）。"""

from pathlib import Path

import pytest

URL = (Path(__file__).parent.parent / "index.html").as_uri()


@pytest.fixture()
def app_page(page):
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL)
    yield page
    assert errors == [], errors


def test_default_page_is_settle(app_page):
    page = app_page
    assert page.locator("#settle").is_visible()
    assert not page.locator("#problem").is_visible()


def test_ting_flow(app_page):
    page = app_page
    page.locator("#tab-ting").click()
    page.wait_for_selector("#candidates button")
    assert page.locator("#problem .tile").count() >= 13
    page.locator("#candidates button").nth(0).click()
    page.locator("#submit").click()
    assert page.locator("#verdict").inner_text() != ""
    assert page.locator("#result tr").count() >= 2  # 表头 + 至少一张胡牌


def test_ting_next_guard(app_page):
    """选了牌未提交时点下一题应先判定，再点才换题。"""
    page = app_page
    page.locator("#tab-ting").click()
    page.wait_for_selector("#candidates button")
    page.locator("#candidates button").nth(0).click()
    page.locator("#next").click()
    assert page.locator("#verdict").inner_text() != ""
    hand_js = "[...document.querySelectorAll('#problem .tile')].map(e => e.dataset.tile).join()"
    hand_before = page.evaluate(hand_js)
    page.locator("#next").click()
    page.wait_for_function(f"prev => {hand_js} !== prev", arg=hand_before)


def test_discard_flow(app_page):
    page = app_page
    page.locator("#tab-discard").click()
    page.wait_for_selector("#rows > div")
    assert page.locator("#rows > div").count() == 1  # 初始只有一排待选
    assert page.locator("#rows > div").nth(0).locator("button.tile").count() == 14

    # 在待选排里每种牌各选一次：每选一张下方多出一排
    tiles = page.eval_on_selector(
        "#rows > div", "e => [...e.querySelectorAll('button.tile')].map(b => b.dataset.tile)")
    kinds = list(dict.fromkeys(tiles))
    for k, t in enumerate(kinds):
        last_row = page.locator("#rows > div").last
        last_row.locator(f'button.tile[data-tile="{t}"]').first.click()
        assert page.locator("#rows > div").count() == k + 2
    assert page.locator("#rows .tile.selected").count() == len(kinds)

    # 点某排已选的牌取消整排，再在待选排选回
    page.locator("#rows > div").nth(0).locator(".tile.selected").click()
    assert page.locator("#rows > div").count() == len(kinds)
    page.locator("#rows > div").last.locator(
        f'button.tile[data-tile="{kinds[0]}"]').first.click()
    assert page.locator("#rows > div").count() == len(kinds) + 1

    # 全选提交：正确的标绿、多选的标红、无漏选排；结果表列出全部下叫打法
    page.locator("#submit").click()
    assert page.locator("#verdict").inner_text() != ""
    assert page.locator("#rows > div").count() == len(kinds)  # 待选排消失
    assert page.locator("#rows .tile.missed").count() == 0
    good = page.locator("#rows .tile.good").count()
    assert good >= 1
    assert page.locator("#rows .tile.bad").count() == len(kinds) - good
    assert page.locator("#result tr").count() == good + 1


def test_settle_flow(app_page):
    page = app_page
    page.locator("#tab-settle").click()
    assert page.locator("#settle").is_visible()
    assert not page.locator("#problem").is_visible()
    assert page.locator("#s-players input").count() == 4

    for i, v in enumerate(["140", "90", "85", "65"]):
        page.locator("#s-players input").nth(i).fill(v)
    page.locator("#s-tea").fill("20")
    page.locator("#s-go").click()
    assert "对账正确" in page.locator("#s-check").inner_text()
    out = page.locator("#s-out").inner_text()
    assert "收 45 元" in out and "付 30 元" in out and "付 5 元" in out

    # 数错筹码应提示差额
    page.locator("#s-players input").nth(0).fill("130")
    page.locator("#s-go").click()
    assert "差 10" in page.locator("#s-check").inner_text()

    # 人数改 3 应重建输入行
    page.locator("#s-count").fill("3")
    assert page.locator("#s-players input").count() == 3

    # 切回练习页应恢复出题
    page.locator("#tab-ting").click()
    page.wait_for_selector("#candidates button")
    assert not page.locator("#settle").is_visible()
