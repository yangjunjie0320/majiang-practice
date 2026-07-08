/* 川麻核心逻辑：牌表示、胡牌判定、倍数、向听/进张、出题。
 *
 * 无依赖、不碰 DOM（供微信小程序 require 复用）。
 * 牌用字符串表示如 "3m"（m=万 s=条 p=筒），计数为长度 27 的数组，
 * 下标 = 花色序号*9 + 点数-1。川麻没有字牌。
 * 规则约定（倍数表、缺一门、逆向出题）见 DESIGN.md。
 */
"use strict";

const Majiang = (() => {
  const SUITS = "msp";
  const SUIT_NAMES = { m: "万", s: "条", p: "筒" };

  // ---- 牌的表示 ----

  function tileIndex(tile) {
    return SUITS.indexOf(tile[1]) * 9 + (Number(tile[0]) - 1);
  }

  function indexToTile(i) {
    return `${(i % 9) + 1}${SUITS[Math.floor(i / 9)]}`;
  }

  function formatTile(tile) {
    return tile[0] + SUIT_NAMES[tile[1]];
  }

  function countsFromTiles(tiles) {
    const counts = new Array(27).fill(0);
    for (const t of tiles) counts[tileIndex(t)] += 1;
    return counts;
  }

  function tilesFromCounts(counts) {
    const tiles = [];
    for (let i = 0; i < 27; i++) for (let c = 0; c < counts[i]; c++) tiles.push(indexToTile(i));
    return tiles;
  }

  function sortTiles(tiles) {
    return [...tiles].sort((a, b) => tileIndex(a) - tileIndex(b));
  }

  function suitsIn(counts) {
    const suits = new Set();
    for (let i = 0; i < 27; i++) if (counts[i] > 0) suits.add(SUITS[Math.floor(i / 9)]);
    return suits;
  }

  // ---- 胡牌判定与倍数 ----

  // 判断 9 张位的计数能否全部拆成刻子和顺子。
  // 贪心（先刻后顺）会漏掉如 [3,4,5,2,1] = 123x3+234+345 的拆法，必须回溯。
  function suitCanFormMelds(block) {
    function walk(i) {
      while (i < 9 && block[i] === 0) i++;
      if (i === 9) return true;
      if (block[i] >= 3) {
        block[i] -= 3;
        if (walk(i)) { block[i] += 3; return true; }
        block[i] += 3;
      }
      if (i <= 6 && block[i + 1] > 0 && block[i + 2] > 0) {
        block[i]--; block[i + 1]--; block[i + 2]--;
        if (walk(i)) { block[i]++; block[i + 1]++; block[i + 2]++; return true; }
        block[i]++; block[i + 1]++; block[i + 2]++;
      }
      return false;
    }
    return walk(0);
  }

  // 4 副刻子/顺子 + 1 对将。
  function isStandardWin(counts) {
    for (let p = 0; p < 27; p++) {
      if (counts[p] < 2) continue;
      counts[p] -= 2;
      let ok = true;
      for (let s = 0; s < 3 && ok; s++) {
        const block = counts.slice(s * 9, s * 9 + 9);
        const total = block.reduce((a, b) => a + b, 0);
        ok = total % 3 === 0 && suitCanFormMelds(block);
      }
      counts[p] += 2;
      if (ok) return true;
    }
    return false;
  }

  function isSevenPairs(counts) {
    let pairs = 0;
    for (const c of counts) {
      if (c % 2 !== 0) return false;
      pairs += c / 2;
    }
    return pairs === 7;
  }

  // 对对胡：存在一个将对，其余全是刻子。
  function isAllTriplets(counts) {
    for (let p = 0; p < 27; p++) {
      if (counts[p] !== 2) continue;
      return counts.every((c, i) => i === p || c === 0 || c === 3);
    }
    return false;
  }

  // 14 张牌是否胡牌（要求缺一门，花猪不能胡）。
  function isWin(counts) {
    if (counts.reduce((a, b) => a + b, 0) !== 14 || suitsIn(counts).size > 2) return false;
    return isSevenPairs(counts) || isStandardWin(counts);
  }

  // 计算 14 张胡牌的倍数和番型列表。
  // 倍数为乘法模型：七对x4 / 对对胡x2，清一色x4，每根x2。
  function fan(counts) {
    let mult = 1;
    const patterns = [];
    let gen = counts.filter((c) => c === 4).length;
    if (isSevenPairs(counts)) {
      // 龙七对 = 七对 + 根，根的倍数并入名称，不再单独列出
      patterns.push(gen > 0 ? "龙七对" : "七对");
      mult *= 4 * 2 ** gen;
      gen = 0;
    } else if (isAllTriplets(counts)) {
      patterns.push("对对胡");
      mult *= 2;
    }
    if (suitsIn(counts).size === 1) {
      patterns.push("清一色");
      mult *= 4;
    }
    if (gen > 0) {
      patterns.push(`根x${gen}`);
      mult *= 2 ** gen;
    }
    if (patterns.length === 0) patterns.push("平胡");
    return { fan: mult, patterns };
  }

  // ---- 向听数与进张 ----

  function sevenPairsShanten(counts) {
    let pairs = 0, kinds = 0;
    for (const c of counts) {
      if (c >= 2) pairs++;
      if (c >= 1) kinds++;
    }
    return 6 - pairs + Math.max(0, 7 - kinds);
  }

  // 4 面子 + 1 将的向听数，经典回溯：枚举面子/搭子拆分取最优。
  function standardShanten(counts) {
    counts = counts.slice();
    let best = 8;

    function evaluate(melds, partials, hasPair) {
      if (melds + partials > 4) partials = 4 - melds;
      const st = 8 - 2 * melds - partials - (hasPair ? 1 : 0);
      if (st < best) best = st;
    }

    function walk(i, melds, partials, hasPair) {
      while (i < 27 && counts[i] === 0) i++;
      if (i === 27) { evaluate(melds, partials, hasPair); return; }
      const suitEnd = (Math.floor(i / 9) + 1) * 9;
      if (counts[i] >= 3) {
        counts[i] -= 3;
        walk(i, melds + 1, partials, hasPair);
        counts[i] += 3;
      }
      if (i + 2 < suitEnd && counts[i + 1] > 0 && counts[i + 2] > 0) {
        counts[i]--; counts[i + 1]--; counts[i + 2]--;
        walk(i, melds + 1, partials, hasPair);
        counts[i]++; counts[i + 1]++; counts[i + 2]++;
      }
      if (counts[i] >= 2) {
        counts[i] -= 2;
        if (!hasPair) walk(i, melds, partials, true);
        walk(i, melds, partials + 1, hasPair);
        counts[i] += 2;
      }
      if (i + 1 < suitEnd && counts[i + 1] > 0) {
        counts[i]--; counts[i + 1]--;
        walk(i, melds, partials + 1, hasPair);
        counts[i]++; counts[i + 1]++;
      }
      if (i + 2 < suitEnd && counts[i + 2] > 0) {
        counts[i]--; counts[i + 2]--;
        walk(i, melds, partials + 1, hasPair);
        counts[i]++; counts[i + 2]++;
      }
      counts[i]--;
      walk(i, melds, partials, hasPair);
      counts[i]++;
    }

    walk(0, 0, 0, false);
    return best;
  }

  // 向听数；missingSuit 为定缺花色（其牌视为废牌）。0 = 已下叫，-1 = 已胡。
  function shanten(counts, missingSuit = null) {
    counts = counts.slice();
    if (missingSuit !== null) {
      const base = SUITS.indexOf(missingSuit) * 9;
      for (let i = base; i < base + 9; i++) counts[i] = 0;
    }
    return Math.min(standardShanten(counts), sevenPairsShanten(counts));
  }

  // 13 张手牌的进张：返回 {shanten, tiles, total}。
  // 进张 = 摸到后向听数下降的牌；枚数按 4 - 手中已有张数计。
  function ukeire(counts, missingSuit) {
    const base = shanten(counts, missingSuit);
    const tiles = [];
    let total = 0;
    for (let i = 0; i < 27; i++) {
      if (missingSuit !== null && SUITS[Math.floor(i / 9)] === missingSuit) continue;
      if (counts[i] >= 4) continue;
      counts[i] += 1;
      if (shanten(counts, missingSuit) < base) {
        tiles.push(indexToTile(i));
        total += 4 - (counts[i] - 1);
      }
      counts[i] -= 1;
    }
    return { shanten: base, tiles, total };
  }

  // ---- 出题（逆向法：从完整胡牌出发构造题目）----

  // 难度分档：按答案数量（能胡几张 / 几种下叫打法）划定范围，
  // 依据 400 题抽样分布，各档占比 15%-45%。
  const DIFFICULTY = {
    ting: { easy: [1, 2], normal: [3, 3], hard: [4, Infinity] },
    discard: { easy: [1, 2], normal: [3, 4], hard: [5, Infinity] },
  };

  function inRange(n, mode, difficulty) {
    const r = DIFFICULTY[mode][difficulty];
    return n >= r[0] && n <= r[1];
  }

  function randInt(rng, n) {
    return Math.floor(rng() * n);
  }

  function choice(rng, arr) {
    return arr[randInt(rng, arr.length)];
  }

  function sampleTwoSuits(rng) {
    const suits = [0, 1, 2];
    suits.splice(randInt(rng, 3), 1);
    return suits;
  }

  // 生成一副缺一门的 14 张胡牌计数，失败返回 null。
  function randomCompleteHand(rng, suits = null) {
    suits = suits || sampleTwoSuits(rng);
    const counts = new Array(27).fill(0);

    function add(idx, n) {
      if (counts[idx] + n > 4) return false;
      counts[idx] += n;
      return true;
    }

    if (rng() < 0.25) {
      // 七对：偶尔用同牌 4 张凑成龙七对
      let need = 7;
      while (need > 0) {
        const idx = choice(rng, suits) * 9 + randInt(rng, 9);
        let take = need === 1 || rng() < 0.8 ? 2 : 4;
        take = Math.min(take, need * 2);
        if (add(idx, take)) need -= take / 2;
      }
      return counts;
    }

    // 4 面子 + 1 将
    if (!add(choice(rng, suits) * 9 + randInt(rng, 9), 2)) return null;
    for (let k = 0; k < 4; k++) {
      const s = choice(rng, suits);
      let ok;
      if (rng() < 0.5) {
        const start = s * 9 + randInt(rng, 7);
        ok = add(start, 1) && add(start + 1, 1) && add(start + 2, 1);
      } else {
        ok = add(s * 9 + randInt(rng, 9), 3);
      }
      if (!ok) return null;
    }
    return counts;
  }

  // 13 张手牌能胡的所有牌及倍数。
  function huTiles(counts) {
    const handSuits = [...new Set(
      counts.flatMap((c, i) => (c > 0 ? [Math.floor(i / 9)] : []))
    )].sort();
    const result = [];
    for (const s of handSuits) {
      for (let i = s * 9; i < s * 9 + 9; i++) {
        if (counts[i] >= 4) continue;
        counts[i] += 1;
        if (isWin(counts)) {
          const f = fan(counts);
          result.push({ tile: indexToTile(i), fan: f.fan, patterns: f.patterns });
        }
        counts[i] -= 1;
      }
    }
    return result;
  }

  // 已下叫题：枚举去掉一张的所有方式。指定难度时按答案数分档筛选，
  // 否则取听牌数最多（最难）的一种。
  function makeTingProblem(rng = Math.random, difficulty = null) {
    for (;;) {
      const counts = randomCompleteHand(rng);
      if (counts === null || !isWin(counts)) continue;
      const variants = [];
      for (let removed = 0; removed < 27; removed++) {
        if (counts[removed] === 0) continue;
        counts[removed] -= 1;
        const tiles = huTiles(counts);
        counts[removed] += 1;
        if (tiles.length > 0) variants.push({ removed, tiles });
      }
      let pool;
      if (difficulty) {
        pool = variants.filter((v) => inRange(v.tiles.length, "ting", difficulty));
      } else {
        const most = Math.max(0, ...variants.map((v) => v.tiles.length));
        pool = variants.filter((v) => v.tiles.length === most);
      }
      if (pool.length === 0) continue;
      const pick = choice(rng, pool);
      counts[pick.removed] -= 1;

      const handSuits = [...new Set(
        counts.flatMap((c, i) => (c > 0 ? [Math.floor(i / 9)] : []))
      )].sort();
      const candidates = handSuits.flatMap((s) =>
        Array.from({ length: 9 }, (_, r) => indexToTile(s * 9 + r)));
      return {
        mode: "ting",
        hand: sortTiles(tilesFromCounts(counts)),
        candidates,
        answer: { hu_tiles: pick.tiles },
      };
    }
  }

  // 14 张手牌中所有打完即下叫的打法及各自听的牌。
  function tingOptions(counts, missingSuit) {
    const options = [];
    for (let x = 0; x < 27; x++) {
      if (counts[x] === 0) continue;
      counts[x] -= 1;
      // 先只算向听，命中 0 才算听牌明细
      if (shanten(counts, missingSuit) === 0) {
        const u = ukeire(counts, missingSuit);
        // total==0 是形式听牌（听的牌全在自己手里），不算有效下叫
        if (u.total > 0) {
          options.push({ tile: indexToTile(x), waits: u.tiles, count: u.total });
        }
      }
      counts[x] += 1;
    }
    return options;
  }

  // 未下叫题：胡牌随机去一张，枚举补一张的所有可能。指定难度时按
  // 答案数分档筛选，否则取能下叫的打法最多（选择最多、最难）的一种。
  function makeDiscardProblem(rng = Math.random, difficulty = null) {
    for (;;) {
      const kept = sampleTwoSuits(rng);
      const missingSuit = SUITS[[0, 1, 2].find((s) => !kept.includes(s))];
      const counts = randomCompleteHand(rng, kept);
      if (counts === null || !isWin(counts)) continue;
      counts[tileIndex(choice(rng, tilesFromCounts(counts)))] -= 1;

      const variants = [];
      for (const s of kept) {
        for (let r = 0; r < 9; r++) {
          const i = s * 9 + r;
          if (counts[i] >= 4) continue;
          counts[i] += 1;
          if (!isWin(counts)) {
            const options = tingOptions(counts, missingSuit);
            if (options.length > 0) variants.push({ add: i, options });
          }
          counts[i] -= 1;
        }
      }
      let pool;
      if (difficulty) {
        pool = variants.filter((v) => inRange(v.options.length, "discard", difficulty));
      } else {
        const most = Math.max(0, ...variants.map((v) => v.options.length));
        pool = variants.filter((v) => v.options.length === most);
      }
      if (pool.length === 0) continue;
      const pick = choice(rng, pool);
      counts[pick.add] += 1;
      pick.options.sort((a, b) => b.count - a.count);
      return {
        mode: "discard",
        hand: sortTiles(tilesFromCounts(counts)),
        missing_suit: missingSuit,
        answer: { best: pick.options.map((d) => d.tile), detail: pick.options },
      };
    }
  }

  // 结账：局中赢家按比例交的茶钱筹码只记比例，真实茶钱现金另结。
  // 结算时把茶钱按人数平分补回每人：输赢 = 筹码 + 茶钱/人数 − 起始。
  // 对账（diff===0，即 Σ筹码+茶钱 = 人数×起始）通过时输赢之和恰为 0。
  function settle(initial, chips, tea) {
    const share = tea / chips.length;
    const deltas = chips.map((c) => c + share - initial);
    const diff = chips.reduce((a, b) => a + b, 0) + tea - initial * chips.length;
    return { share, deltas, diff };
  }

  return {
    SUITS, SUIT_NAMES,
    tileIndex, indexToTile, formatTile,
    countsFromTiles, tilesFromCounts, sortTiles, suitsIn,
    isWin, fan, shanten, ukeire,
    makeTingProblem, makeDiscardProblem, settle,
  };
})();

if (typeof module !== "undefined") module.exports = Majiang;
