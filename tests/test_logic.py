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
  // 龙七对：4 张同牌算 2 对。1111m+6m+四个对子摸 6m 即胡，向听应为 0
  const dragon = c("1m","1m","1m","1m","6m","2s","2s","3s","3s","4s","4s","5s","5s");
  check("龙七对下叫 = 0", M.shanten(dragon) === 0);
  const u3 = M.ukeire(dragon, null);
  check("龙七对进张听 6m", u3.shanten === 0 && u3.tiles.includes("6m") && u3.total >= 3);
  // 两个 4 张 + 1 对 + 3 单张 = 5 对，1 向听
  check("双龙七对 1 向听", M.shanten(
    c("1m","1m","1m","1m","3m","3m","3m","3m","2s","2s","5m","7m","9m")) === 1);
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

  // ---- 副露（碰/杠）----
  const pengS = [{ type: "peng", tile: "7s" }];
  check("副露平胡", M.isWin(c("1m","2m","3m","4m","5m","6m","7m","8m","9m","5s","5s"), pengS));
  check("副露张数不符不胡", !M.isWin(
    c("1m","2m","3m","4m","5m","6m","7m","8m","9m","1s","1s","1s","2s","2s"), pengS));
  check("副露算花猪", !M.isWin(c("1m","2m","3m","4m","5m","6m","7m","8m","9m","5p","5p"), pengS));
  const fanA = M.fan(c("1m","1m","1m","3m","3m","3m","5m","5m"),
    [{ type: "peng", tile: "7s" }, { type: "gang", tile: "9s" }]);
  check("副露对对胡+杠根", fanA.fan === 4
    && fanA.patterns.includes("对对胡") && fanA.patterns.includes("根x1"));
  const fanB = M.fan(c("1m","2m","3m","4m","5m","6m","5m","5m"),
    [{ type: "gang", tile: "9m" }, { type: "peng", tile: "7m" }]);
  check("副露清一色+杠根", fanB.fan === 8
    && fanB.patterns.includes("清一色") && fanB.patterns.includes("根x1"));
  const fanC = M.fan(c("1m","2m","3m","4m","5m","6m","6s","7s","8s","9s","9s"),
    [{ type: "peng", tile: "7s" }]);
  check("碰加手内一张算根", fanC.fan === 2 && fanC.patterns.includes("根x1"));
  check("副露向听: 差将对", M.shanten(
    c("1m","2m","3m","4m","5m","6m","1s","1s","1s","2s"), null, 1) === 0);
  check("副露不能七对", M.shanten(
    c("1m","1m","3m","3m","5m","5m","7m","7m","9m","9m"), null, 1) > 0);
  const u4 = M.ukeire(c("1m","2m","3m","4m","5m","6m","3s","4s","9s","9s"), null,
    [{ type: "peng", tile: "5s" }]);
  check("副露进张扣除碰占的枚数", u4.shanten === 0 && u4.tiles.includes("2s")
    && u4.tiles.includes("5s") && u4.total === 5);
  const u5 = M.ukeire(c("1m","2m","3m","4m","5m","6m","7m","8m","9m","5s"), null,
    [{ type: "peng", tile: "5s" }]);
  check("被副露占满的听是形式听牌", u5.shanten === 0 && u5.total === 0);

  // ---- 出题器不变量（种子随机数保证可复现）----
  const mulberry32 = a => () => {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };

  const meldsExtra = (melds) => {
    const extra = new Array(27).fill(0);
    melds.forEach(d => { extra[M.tileIndex(d.tile)] += d.type === "peng" ? 3 : 4; });
    return extra;
  };

  const rng1 = mulberry32(42);
  for (let k = 0; k < 20; k++) {
    const p = M.makeTingProblem(rng1);
    const m = p.melds.length;
    check(`ting#${k} 张数`, m <= 2 && p.hand.length === 13 - 3 * m);
    check(`ting#${k} 副露类型`, p.melds.every(
      d => ["peng", "gang"].includes(d.type)));
    const counts = M.countsFromTiles(p.hand);
    const extra = meldsExtra(p.melds);
    check(`ting#${k} 张数上限`, counts.every((c2, i) => c2 + extra[i] <= 4));
    const suits = M.suitsIn(counts);
    p.melds.forEach(d => suits.add(d.tile[1]));
    check(`ting#${k} ≤2门`, suits.size <= 2);
    check(`ting#${k} 有答案`, p.answer.hu_tiles.length > 0);
    // 穷举所有可摸的牌，胡牌集合必须与答案完全相等
    const ans = new Set(p.answer.hu_tiles.map(h => h.tile));
    for (let i = 0; i < 27; i++) {
      if (counts[i] + extra[i] >= 4) continue;
      counts[i] += 1;
      const win = M.isWin(counts, p.melds);
      counts[i] -= 1;
      check(`ting#${k} 答案完备 ${M.indexToTile(i)}`,
        win === ans.has(M.indexToTile(i)));
    }
    for (const h of p.answer.hu_tiles) check(`ting#${k} ${h.tile} 倍数≥1`, h.fan >= 1);
  }

  const rng2 = mulberry32(7);
  for (let k = 0; k < 10; k++) {
    const p = M.makeDiscardProblem(rng2);
    const m = p.melds.length;
    check(`discard#${k} 张数`, m <= 2 && p.hand.length === 14 - 3 * m);
    check(`discard#${k} 有答案`, p.answer.best.length > 0);
    check(`discard#${k} 答案在手牌中`, p.answer.best.every(t => p.hand.includes(t)));
    check(`discard#${k} 不含定缺门`, p.hand.every(t => !t.endsWith(p.missing_suit))
      && p.melds.every(d => !d.tile.endsWith(p.missing_suit)));
    const counts = M.countsFromTiles(p.hand);
    const extra = meldsExtra(p.melds);
    check(`discard#${k} 张数上限`, counts.every((c2, i) => c2 + extra[i] <= 4));
    // 穷举所有弃牌×摸牌（isWin 直判），必须与答案集合完全相等
    const ref = [];
    for (let x = 0; x < 27; x++) {
      if (counts[x] === 0) continue;
      counts[x] -= 1;
      const waits = [];
      let total = 0;
      for (let w = 0; w < 27; w++) {
        if (counts[w] + extra[w] >= 4) continue;
        counts[w] += 1;
        if (M.isWin(counts, p.melds)) {
          waits.push(M.indexToTile(w));
          total += 4 - extra[w] - (counts[w] - 1);
        }
        counts[w] -= 1;
      }
      counts[x] += 1;
      if (waits.length > 0) ref.push({ tile: M.indexToTile(x), waits, count: total });
    }
    const norm = (a) => JSON.stringify([...a]
      .sort((u, v) => M.tileIndex(u.tile) - M.tileIndex(v.tile))
      .map(d => [d.tile, [...d.waits].sort(), d.count]));
    check(`discard#${k} 答案与穷举一致`, norm(ref) === norm(p.answer.detail));
  }

  // ---- 困难档副露题池 ----
  const rng4 = mulberry32(2024);
  let pooledT = 0;
  for (let k = 0; k < 60 && pooledT < 3; k++) {
    const p = M.makeTingProblem(rng4, "hard");
    if (p.melds.length === 0) continue;
    pooledT += 1;
    check(`pool-ting#${pooledT} 答案数≥4`, p.answer.hu_tiles.length >= 4);
    check(`pool-ting#${pooledT} 张数`, p.hand.length === 13 - 3 * p.melds.length);
  }
  check("听牌题池命中≥3", pooledT >= 3);
  let pooledD = 0;
  for (let k = 0; k < 30 && pooledD < 2; k++) {
    const p = M.makeDiscardProblem(rng4, "hard");
    if (p.melds.length === 0) continue;
    pooledD += 1;
    check(`pool-discard#${pooledD} 答案数≥5`, p.answer.best.length >= 5);
    check(`pool-discard#${pooledD} 张数`, p.hand.length === 14 - 3 * p.melds.length);
  }
  check("下叫题池命中≥2", pooledD >= 2);

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

  // ---- 结账：输赢 = 筹码 + 茶钱/人数 − 起始，对账 = Σ筹码+茶钱−人数×起始 ----
  const st = M.settle(100, [140, 90, 85, 65], 20);
  check("settle 平分茶钱", st.share === 5);
  check("settle 输赢", JSON.stringify(st.deltas) === JSON.stringify([45, -5, -10, -30]));
  check("settle 对账平", st.diff === 0);
  check("settle 和为零", st.deltas.reduce((a, b) => a + b, 0) === 0);
  check("settle 对账差", M.settle(100, [100, 100, 100, 90], 0).diff === -10);
  check("settle 三人", JSON.stringify(M.settle(50, [80, 20, 50], 0).deltas)
    === JSON.stringify([30, -30, 0]));
  // 茶钱除不尽：金额按分守恒分配，总和恰为 0（差额分从第一家起补）
  const st2 = M.settle(100, [100, 100, 99], 1);
  check("settle 除不尽守恒", JSON.stringify(st2.deltas)
    === JSON.stringify([0.34, 0.33, -0.67]) && st2.diff === 0);
  const st3 = M.settle(100, [103, 99, 88], 10);
  check("settle 除不尽和为零", st3.diff === 0
    && Math.round(st3.deltas.reduce((a, b) => a + b, 0) * 100) === 0
    && JSON.stringify(st3.deltas) === JSON.stringify([6.34, 2.33, -8.67]));

  return fails;
}
"""


def test_logic(page):
    page.goto("about:blank")
    page.add_script_tag(path=str(ROOT / "assets" / "pools.js"))
    page.add_script_tag(path=str(ROOT / "majiang.js"))
    fails = page.evaluate(CHECKS)
    assert fails == [], "\n".join(fails)


def test_pool_sizes(page):
    """题池与离线枚举的困难题数量一致（见 scripts/gen_pools.py）。"""
    page.goto("about:blank")
    page.add_script_tag(path=str(ROOT / "assets" / "pools.js"))
    page.add_script_tag(path=str(ROOT / "majiang.js"))
    sizes = page.evaluate(
        "() => ['ting1','ting2','discard1','discard2']"
        ".map(k => Majiang.decodePool(k).length)")
    assert sizes == [4422, 150, 33898, 188]
