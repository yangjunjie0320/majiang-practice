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
      const m2 = k.match(/^(\\w+)\\[(\\d+)\\]\\[(\\d+)\\]\\.(\\w+)$/);
      const m1 = k.match(/^(\\w+)\\[(\\d+)\\]\\.(\\w+)$/);
      if (m2) this.data[m2[1]][Number(m2[2])][Number(m2[3])][m2[4]] = v;
      else if (m1) this.data[m1[1]][Number(m1[2])][m1[3]] = v;
      else this.data[k] = v;
    }
  };
  const flat = (rows) => [].concat(...rows);

  // 已下叫模式：全选正确答案应判对
  inst.onLoad();
  check("ting 手牌 13", inst.data.hand.length === 13);
  check("ting 有候选", flat(inst.data.candidateRows).length >= 9);
  check("候选牌花色分行", inst.data.candidateRows.every(
    (row) => row.every((c) => c.suit === row[0].suit)));
  const correct = new Set(inst.problem.answer.hu_tiles.map((h) => h.tile));
  flat(inst.data.candidateRows).forEach((c) => { c.sel = correct.has(c.tile); });
  inst.submit();
  check("ting 判定正确", inst.data.verdictOk === true);
  check("ting 结果行数", inst.data.tingRows.length === correct.size);
  check("ting 标注 good", flat(inst.data.candidateRows)
    .filter((c) => c.mark === "good").length === correct.size);

  // 未下叫模式：打最优牌应判对
  inst.setData({ mode: "discard" });
  inst.newProblem();
  check("discard 手牌 14", inst.data.hand.length === 14);
  check("discard 定缺名", ["万", "条", "筒"].includes(inst.data.missingName));
  const bestTile = inst.problem.answer.best[0];
  const idx = inst.data.hand.findIndex((c) => c.tile === bestTile);
  inst.discardTap({ currentTarget: { dataset: { i: idx } } });
  check("discard 判定正确", inst.data.verdictOk === true);
  check("discard 结果非空", inst.data.discardRows.length > 0);

  // 切换难度应出新题且不报错
  inst.setDifficulty({ currentTarget: { dataset: { diff: "hard" } } });
  check("难度切换", inst.data.difficulty === "hard" && inst.data.answered === false);

  // 防误点：选牌未提交点下一题应先判定
  inst.setData({ mode: "ting" });
  inst.newProblem();
  inst.data.candidateRows[0][0].sel = true;
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
