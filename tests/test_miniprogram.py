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

  // 默认打开结账页，不出题
  inst.onLoad();
  check("默认结账页", inst.data.mode === "settle" && inst.data.hand.length === 0);

  // 已下叫模式：全选正确答案应判对
  inst.switchMode({ currentTarget: { dataset: { mode: "ting" } } });
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

  // 未下叫模式：每排选一张，选齐所有下叫打法应判对
  inst.setData({ mode: "discard" });
  inst.newProblem();
  check("discard 初始一排", inst.data.rows.length === 1);
  check("discard 每排 14 张", inst.data.rows[0].tiles.length === 14);
  check("discard 定缺名", ["万", "条", "筒"].includes(inst.data.missingName));
  const best = inst.problem.answer.best;
  best.forEach((t, k) => {
    const idx = inst.problem.hand.indexOf(t);
    inst.discardTap({ currentTarget: { dataset: { r: k, i: idx } } });
  });
  check("discard 排数", inst.data.rows.length === best.length + 1);
  // 点第一排已选的牌取消整排，再在待选排选回
  inst.discardTap({ currentTarget: { dataset: { r: 0, i: inst.problem.hand.indexOf(best[0]) } } });
  check("discard 取消一排", inst.data.rows.length === best.length);
  inst.discardTap({ currentTarget: {
    dataset: { r: best.length - 1, i: inst.problem.hand.indexOf(best[0]) } } });
  check("discard 选回", inst.data.rows.length === best.length + 1);
  inst.submit();
  check("discard 判定正确", inst.data.verdictOk === true);
  check("discard 待选排消失", inst.data.rows.length === best.length);
  check("discard 全对标绿", inst.data.rows.every(
    (row) => row.tiles.filter((t) => t.mark === "good").length === 1));
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

  // 结账模式：填数结算应出正确结果
  inst.switchMode({ currentTarget: { dataset: { mode: "settle" } } });
  check("settle 模式", inst.data.mode === "settle");
  inst.sInitInput({ detail: { value: "100" } });
  ["140", "90", "85", "65"].forEach((v, i) =>
    inst.sChipInput({ currentTarget: { dataset: { i } }, detail: { value: v } }));
  inst.sTeaInput({ detail: { value: "20" } });
  inst.doSettle();
  check("settle 行数", inst.data.sRows.length === 4);
  check("settle 对账平", inst.data.sBalanced === true);
  check("settle 甲收45", inst.data.sRows[0].text === "收 45 元");
  check("settle 丁付30", inst.data.sRows[3].text === "付 30 元");
  inst.sChipInput({ currentTarget: { dataset: { i: 0 } }, detail: { value: "130" } });
  inst.doSettle();
  check("settle 对账差", inst.data.sBalanced === false
    && inst.data.sCheck.includes("差 10"));
  inst.sCountInput({ detail: { value: "3" } });
  check("settle 人数改3", inst.data.sChips.length === 3);

  return fails;
}
"""


def test_page_logic(page):
    page.goto("about:blank")
    page.add_script_tag(path=str(ROOT / "miniprogram" / "majiang.js"))
    src = (ROOT / "miniprogram" / "pages" / "index" / "index.js").read_text()
    fails = page.evaluate(HARNESS, src)
    assert fails == [], "\n".join(fails)
