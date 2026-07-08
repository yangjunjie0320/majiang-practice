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


def test_ting_flow(app_page):
    page = app_page
    page.wait_for_selector("#candidates button")
    assert page.locator("#problem .tile").count() >= 13
    page.locator("#candidates button").nth(0).click()
    page.locator("#submit").click()
    assert page.locator("#verdict").inner_text() != ""
    assert page.locator("#result tr").count() >= 2  # 表头 + 至少一张胡牌


def test_ting_next_guard(app_page):
    """选了牌未提交时点下一题应先判定，再点才换题。"""
    page = app_page
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
    page.wait_for_selector("#problem button.tile")
    assert page.locator("#problem button.tile").count() == 14
    page.locator("#problem button.tile").nth(0).click()
    verdict = page.locator("#verdict").inner_text()
    assert "下叫" in verdict
    assert page.locator("#result tr").count() >= 2


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
