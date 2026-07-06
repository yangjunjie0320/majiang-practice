"""majiang.js 逻辑测试：Playwright 注入脚本后在浏览器里跑断言，返回失败列表。"""

from pathlib import Path

ROOT = Path(__file__).parent.parent

CHECKS = """
() => {
  const M = Majiang;
  const fails = [];
  const c = (...tiles) => M.countsFromTiles(tiles);
  const check = (name, cond) => { if (!cond) fails.push(name); };
  const eqFan = (name, counts, fan, patterns) => {
    if (!M.isWin(counts)) { fails.push(name + ": 应胡而未胡"); return; }
    const f = M.fan(counts);
    if (f.fan !== fan || JSON.stringify([...f.patterns].sort()) !== JSON.stringify([...patterns].sort()))
      fails.push(`${name}: got ${f.fan} ${f.patterns}, want ${fan} ${patterns}`);
  };

  // ---- 胡牌与倍数 ----
  eqFan("平胡", c("1m","2m","3m","4m","5m","6m","7m","8m","9m","1s","1s","1s","2s","2s"),
        1, ["平胡"]);
  // 1112345678999m + 9m：将=11，拆 123 456 789 999，需要正确的拆分搜索
  eqFan("九莲", c("1m","1m","1m","2m","3m","4m","5m","6m","7m","8m","9m","9m","9m","9m"),
        8, ["清一色","根x1"]);
  eqFan("对对胡", c("1m","1m","1m","3m","3m","3m","7s","7s","7s","9s","9s","9s","5m","5m"),
        2, ["对对胡"]);
  eqFan("清一色", c("1m","2m","3m","4m","5m","6m","7m","8m","9m","2m","3m","4m","5m","5m"),
        4, ["清一色"]);
  eqFan("七对", c("1m","1m","3m","3m","5m","5m","7m","7m","2s","2s","4s","4s","6s","6s"),
        4, ["七对"]);
  eqFan("龙七对", c("1m","1m","1m","1m","3m","3m","5m","5m","2s","2s","4s","4s","6s","6s"),
        8, ["龙七对"]);
  eqFan("清七对", c("1m","1m","2m","2m","3m","3m","4m","4m","5m","5m","6m","6m","7m","7m"),
        16, ["七对","清一色"]);
  // 2222m 作为 222 刻子 + 2 进顺子 234：平胡带一根
  eqFan("根", c("2m","2m","2m","2m","3m","4m","5m","6m","7m","1s","1s","1s","9s","9s"),
        2, ["根x1"]);
  // 万: 334455667788 + 99 将，多种拆法
  check("多解拆分", M.isWin(c("3m","3m","4m","4m","5m","5m","6m","6m","7m","7m","8m","8m","9m","9m")));
  // 三门齐 = 花猪，不能胡
  check("花猪不能胡", !M.isWin(c("1m","2m","3m","4m","5m","6m","7m","8m","9m","1s","1s","1s","2p","2p")));
  check("未成型不胡", !M.isWin(c("1m","2m","4m","5m","7m","8m","1s","2s","4s","5s","7s","8s","9s","9s")));

  // ---- 向听与进张 ----
  check("已胡 = -1", M.shanten(
    c("1m","2m","3m","4m","5m","6m","7m","8m","9m","1s","1s","1s","2s","2s")) === -1);
  check("下叫 = 0", M.shanten(
    c("1m","2m","3m","4m","5m","6m","7m","8m","9m","1s","1s","1s","2s")) === 0);
  // 三副顺子 + 两个搭子 + 将，差一步下叫
  check("1 向听", M.shanten(
    c("1m","2m","3m","4m","5m","6m","7m","8m","1s","2s","5s","5s","9s")) === 1);
  // 5 对 + 2 单张 = 1 向听（七对路线）
  check("七对 1 向听", M.shanten(
    c("1m","1m","3m","3m","5m","5m","7m","7m","2s","2s","4s","6s","8s")) === 1);
  // 手里有定缺门的刻子也不能用
  const dead = c("1p","1p","1p","4m","5m","6m","7m","8m","9m","1s","1s","1s","2s");
  check("定缺废牌: 不定缺是下叫", M.shanten(dead, null) === 0);
  check("定缺废牌: 定缺筒后退", M.shanten(dead, "p") > 0);
  const u1 = M.ukeire(
    c("1m","2m","3m","4m","5m","6m","7m","8m","9m","1s","1s","1s","2s"), null);
  check("进张: 下叫听 2s", u1.shanten === 0 && u1.tiles.includes("2s") && u1.total >= 3);
  const u2 = M.ukeire(
    c("1m","2m","3m","4m","5m","6m","7m","8m","1s","2s","5s","5s","9p"), "p");
  check("进张不含定缺门", u2.tiles.every(t => !t.endsWith("p")));

  // ---- 出题器不变量（种子随机数保证可复现）----
  const mulberry32 = a => () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };

  const rng1 = mulberry32(42);
  for (let k = 0; k < 20; k++) {
    const p = M.makeTingProblem(rng1);
    check(`ting#${k} 13张`, p.hand.length === 13);
    const counts = M.countsFromTiles(p.hand);
    check(`ting#${k} ≤2门`, M.suitsIn(counts).size <= 2);
    check(`ting#${k} 有答案`, p.answer.hu_tiles.length > 0);
    for (const h of p.answer.hu_tiles) {
      counts[M.tileIndex(h.tile)] += 1;
      check(`ting#${k} ${h.tile} 真胡`, M.isWin(counts));
      check(`ting#${k} ${h.tile} 倍数≥1`, h.fan >= 1);
      counts[M.tileIndex(h.tile)] -= 1;
    }
  }

  const rng2 = mulberry32(7);
  for (let k = 0; k < 10; k++) {
    const p = M.makeDiscardProblem(rng2);
    check(`discard#${k} 14张`, p.hand.length === 14);
    check(`discard#${k} 有答案`, p.answer.best.length > 0);
    check(`discard#${k} 答案在手牌中`, p.answer.best.every(t => p.hand.includes(t)));
    check(`discard#${k} 不含定缺门`, p.hand.every(t => !t.endsWith(p.missing_suit)));
    const counts = M.countsFromTiles(p.hand);
    check(`discard#${k} ≤2门`, M.suitsIn(counts).size <= 2);
    for (const d of p.answer.detail) {
      check(`discard#${k} 打${d.tile} 枚数>0`, d.count > 0);
      counts[M.tileIndex(d.tile)] -= 1;
      check(`discard#${k} 打${d.tile} 即下叫`, M.shanten(counts, p.missing_suit) === 0);
      for (const w of d.waits) {
        counts[M.tileIndex(w)] += 1;
        check(`discard#${k} 打${d.tile} 听${w} 真胡`, M.isWin(counts));
        counts[M.tileIndex(w)] -= 1;
      }
      counts[M.tileIndex(d.tile)] += 1;
    }
  }

  // ---- 难度分档：答案数必须落在档位内 ----
  const rng3 = mulberry32(99);
  for (const [diff, lo, hi] of [["easy",1,2],["normal",3,3],["hard",4,99]]) {
    for (let k = 0; k < 5; k++) {
      const n = M.makeTingProblem(rng3, diff).answer.hu_tiles.length;
      check(`ting-${diff} 答案数 ${n}`, n >= lo && n <= hi);
    }
  }
  for (const [diff, lo, hi] of [["easy",1,2],["normal",3,4],["hard",5,99]]) {
    for (let k = 0; k < 5; k++) {
      const n = M.makeDiscardProblem(rng3, diff).answer.best.length;
      check(`discard-${diff} 答案数 ${n}`, n >= lo && n <= hi);
    }
  }

  return fails;
}
"""


def test_logic(page):
    page.goto("about:blank")
    page.add_script_tag(path=str(ROOT / "majiang.js"))
    fails = page.evaluate(CHECKS)
    assert fails == [], "\n".join(fails)
