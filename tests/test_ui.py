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
    hand_before = page.locator("#problem").inner_text()
    page.locator("#next").click()
    page.wait_for_function(
        "prev => document.getElementById('problem').innerText !== prev",
        arg=hand_before,
    )


def test_discard_flow(app_page):
    page = app_page
    page.locator("#tab-discard").click()
    page.wait_for_selector("#problem button.tile")
    assert page.locator("#problem button.tile").count() == 14
    page.locator("#problem button.tile").nth(0).click()
    verdict = page.locator("#verdict").inner_text()
    assert "下叫" in verdict
    assert page.locator("#result tr").count() >= 2
