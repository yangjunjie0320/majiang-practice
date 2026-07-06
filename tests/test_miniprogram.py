"""小程序工程测试：majiang.js 副本同步 + 页面逻辑冒烟（桩模拟 Page/setData）。"""

from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_majiang_js_copies_in_sync():
    assert (ROOT / "majiang.js").read_text() == (
        ROOT / "miniprogram" / "majiang.js"
    ).read_text(), "miniprogram/majiang.js 与根目录 majiang.js 不一致，请重新复制"


HARNESS = """
(src) => {
  const fails = [];
  const check = (name, cond) => { if (!cond) fails.push(name); };

  let cfg;
  new Function("Page", "require", src)((c) => { cfg = c; }, () => Majiang);
  const inst = Object.create(cfg);
  inst.data = JSON.parse(JSON.stringify(cfg.data));
  inst.setData = function (patch) {
    for (const [k, v] of Object.entries(patch)) {
      const m = k.match(/^(\\w+)\\[(\\d+)\\]\\.(\\w+)$/);
      if (m) this.data[m[1]][Number(m[2])][m[3]] = v;
      else this.data[k] = v;
    }
  };

  // 已下叫模式：全选正确答案应判对
  inst.onLoad();
  check("ting 手牌 13", inst.data.hand.length === 13);
  check("ting 有候选", inst.data.candidates.length >= 9);
  const correct = new Set(inst.problem.answer.hu_tiles.map((h) => h.tile));
  inst.data.candidates.forEach((c) => { c.sel = correct.has(c.tile); });
  inst.submit();
  check("ting 判定正确", inst.data.verdictOk === true);
  check("ting 结果行数", inst.data.tingRows.length === correct.size);
  check("ting 标注 good", inst.data.candidates.filter((c) => c.mark === "good").length === correct.size);

  // 未下叫模式：打最优牌应判对
  inst.setData({ mode: "discard" });
  inst.newProblem();
  check("discard 手牌 14", inst.data.hand.length === 14);
  check("discard 定缺名", ["万", "条", "筒"].includes(inst.data.missingName));
  const bestTile = inst.problem.answer.best[0];
  const idx = inst.data.hand.findIndex((h) => h.tile === bestTile);
  inst.discardTap({ currentTarget: { dataset: { i: idx } } });
  check("discard 判定正确", inst.data.verdictOk === true);
  check("discard 结果非空", inst.data.discardRows.length > 0);

  // 防误点：换到新题后选牌未提交点下一题应先判定
  inst.setData({ mode: "ting" });
  inst.newProblem();
  inst.data.candidates[0].sel = true;
  inst.next();
  check("next 先判定", inst.data.answered === true);

  return fails;
}
"""


def test_page_logic(page):
    page.goto("about:blank")
    page.add_script_tag(path=str(ROOT / "miniprogram" / "majiang.js"))
    src = (ROOT / "miniprogram" / "pages" / "index" / "index.js").read_text()
    fails = page.evaluate(HARNESS, src)
    assert fails == [], "\n".join(fails)
