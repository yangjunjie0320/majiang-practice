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

  // 副露每种牌占用的张数（碰 3、杠 4），长度 27。
  function meldExtra(melds) {
    const extra = new Array(27).fill(0);
    for (const meld of melds) {
      extra[tileIndex(meld.tile)] += meld.type === "peng" ? 3 : 4;
    }
    return extra;
  }

  // 暗牌是否胡牌（要求缺一门，花猪不能胡；门数连副露一起算）。
  // melds 为副露（碰/杠，杠不分明暗），暗牌张数须为 14 - 3*副露数；
  // 副露只有刻子类，isStandardWin 对任意 3k+2 张通用，无需知道副露。
  function isWin(counts, melds = []) {
    if (counts.reduce((a, b) => a + b, 0) !== 14 - 3 * melds.length) return false;
    const suits = suitsIn(counts);
    for (const meld of melds) suits.add(meld.tile[1]);
    if (suits.size > 2) return false;
    return isSevenPairs(counts) || isStandardWin(counts);
  }

  // 计算胡牌的倍数和番型列表（counts 为暗牌，melds 为副露）。
  // 倍数为乘法模型：七对x4 / 对对胡x2，清一色x4，每根x2。
  // 根 = 暗牌+副露合计 4 张同牌（杠必是根，碰 3 张加手内 1 张也算根）；
  // 对对胡只看暗牌（副露必为刻子类）；清一色连副露算门数。
  function fan(counts, melds = []) {
    const total = melds.length === 0 ? counts : counts.slice();
    if (melds.length > 0) {
      const extra = meldExtra(melds);
      for (let i = 0; i < 27; i++) total[i] += extra[i];
    }
    let mult = 1;
    const patterns = [];
    let gen = total.filter((c) => c === 4).length;
    if (isSevenPairs(counts)) {
      // 龙七对 = 七对 + 根，根的倍数并入名称，不再单独列出
      patterns.push(gen > 0 ? "龙七对" : "七对");
      mult *= 4 * 2 ** gen;
      gen = 0;
    } else if (isAllTriplets(counts)) {
      patterns.push("对对胡");
      mult *= 2;
    }
    if (suitsIn(total).size === 1) {
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

  // 川麻七对允许 4 张同牌算 2 对（龙七对），对子数按 floor(c/2) 计；
  // 13 张最多 6 对故不会为负，14 张七对成牌恰好返回 -1。
  function sevenPairsShanten(counts) {
    let pairs = 0;
    for (const c of counts) pairs += c >> 1;
    return 6 - pairs;
  }

  // 4 面子 + 1 将的向听数，经典回溯：枚举面子/搭子拆分取最优。
  // meldCount 组副露记为已完成的面子（回溯起点），公式不变。
  function standardShanten(counts, meldCount = 0) {
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

    walk(0, meldCount, 0, false);
    return best;
  }

  // 向听数；missingSuit 为定缺花色（其牌视为废牌）。0 = 已下叫，-1 = 已胡。
  // meldCount 为副露组数；有副露不能七对。
  function shanten(counts, missingSuit = null, meldCount = 0) {
    counts = counts.slice();
    if (missingSuit !== null) {
      const base = SUITS.indexOf(missingSuit) * 9;
      for (let i = base; i < base + 9; i++) counts[i] = 0;
    }
    const std = standardShanten(counts, meldCount);
    return meldCount > 0 ? std : Math.min(std, sevenPairsShanten(counts));
  }

  // 13-3m 张暗牌的进张：返回 {shanten, tiles, total}。
  // 进张 = 摸到后向听数下降的牌；枚数按 4 - 暗牌张数 - 副露占用计，
  // 被自家副露占满的牌不算进张（碰掉 3 张后只剩 1 枚，杠掉则为 0）。
  function ukeire(counts, missingSuit, melds = []) {
    const extra = meldExtra(melds);
    const base = shanten(counts, missingSuit, melds.length);
    const tiles = [];
    let total = 0;
    for (let i = 0; i < 27; i++) {
      if (missingSuit !== null && SUITS[Math.floor(i / 9)] === missingSuit) continue;
      if (counts[i] + extra[i] >= 4) continue;
      counts[i] += 1;
      if (shanten(counts, missingSuit, melds.length) < base) {
        tiles.push(indexToTile(i));
        total += 4 - extra[i] - (counts[i] - 1);
      }
      counts[i] -= 1;
    }
    return { shanten: base, tiles, total };
  }

  // ---- 出题（题库式：全集离线枚举按格抽样，运行时查表抽题）----

  // 难度分档：按答案数量（能胡几张 / 几种下叫打法）划定范围。
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

  // ---- 题库（assets/pools.js，scripts/gen_pools.py 离线枚举生成）----
  // 每格 = (模式 t/d, 副露数 m, 胡法数量 n) 的暗牌形样本（<=100，
  // 固定万/条两门）。出题 = 查权重表抽格 → 洗牌袋抽形 → 置换花色配副露。

  let poolsSource; // undefined = 未探测；null = 不可用
  const poolCache = {};

  function getPoolsSource() {
    if (poolsSource !== undefined) return poolsSource;
    if (typeof MajiangPools !== "undefined") {
      poolsSource = MajiangPools; // 网页：script 标签引入的全局
    } else if (typeof require !== "undefined") {
      try {
        poolsSource = require("./pools.js"); // 小程序：同目录副本
      } catch (e) {
        poolsSource = null;
      }
    } else {
      poolsSource = null;
    }
    return poolsSource;
  }

  // base64 → 差分 varint → 递增的 base-5 编码数组（编码 < 5^18，Number 精确）。
  function decodePool(name) {
    if (poolCache[name] !== undefined) return poolCache[name];
    const src = getPoolsSource();
    if (!src || !src[name]) {
      poolCache[name] = null;
      return null;
    }
    const B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    const rev = {};
    for (let i = 0; i < 64; i++) rev[B64[i]] = i;
    const list = [];
    let buf = 0, bits = 0, prev = 0, x = 0, mult = 1;
    for (const ch of src[name]) {
      if (ch === "=") break;
      buf = (buf << 6) | rev[ch];
      bits += 6;
      if (bits >= 8) {
        bits -= 8;
        const b = (buf >> bits) & 255;
        buf &= (1 << bits) - 1;
        x += (b & 127) * mult;
        if (b & 128) {
          mult *= 128;
        } else {
          prev += x;
          list.push(prev);
          x = 0;
          mult = 1;
        }
      }
    }
    poolCache[name] = list;
    return list;
  }

  // 副露 0-4 组的目标出题比例（贴近实战：碰杠常见、门清少数），一处可调。
  const MELD_WEIGHTS = [30, 35, 25, 8, 2];
  // 各难度档内胡法数量的权重；稀有大听口给低权重，避免高频撞脸。
  const TIER_N = {
    ting: {
      easy: { 1: 50, 2: 50 },
      normal: { 3: 100 },
      hard: { 4: 40, 5: 30, 6: 15, 7: 8, 8: 5, 9: 2 },
    },
    discard: {
      easy: { 1: 50, 2: 50 },
      normal: { 3: 60, 4: 40 },
      hard: { 5: 55, 6: 30, 7: 10, 8: 5 },
    },
  };

  function weightedPick(rng, table) {
    const keys = Object.keys(table);
    let sum = 0;
    for (const k of keys) sum += table[k];
    let r = rng() * sum;
    for (const k of keys) {
      r -= table[k];
      if (r < 0) return Number(k);
    }
    return Number(keys[keys.length - 1]);
  }

  // 洗牌袋：每格无放回发题、发完自动重洗——一轮内绝无重复且间隔最大，
  // 比"随机+已做退避"省状态且无拒绝开销。会话内存态，不跨会话记录。
  const bags = {};
  function bagDraw(rng, key, list) {
    let bag = bags[key];
    if (!bag || bag.pos >= bag.order.length) {
      const order = list.map((_, i) => i);
      for (let i = order.length - 1; i > 0; i--) {
        const j = randInt(rng, i + 1);
        const t = order[i];
        order[i] = order[j];
        order[j] = t;
      }
      bag = bags[key] = { order, pos: 0 };
    }
    const v = list[bag.order[bag.pos]];
    bag.pos += 1;
    return v;
  }

  // 由一个暗牌形构造题目：随机置换花色、随机配副露（碰需该牌暗牌 ≤1 张、
  // 杠需 0 张），再按副露上下文重算答案。副露可能占满某个所听的牌，
  // 答案数掉出难度档时返回 null 由调用方重抽。
  function buildProblem(rng, mode, meldCount, enc, tier) {
    const perm = [0, 1, 2];
    for (let i = 2; i > 0; i--) {
      const j = randInt(rng, i + 1);
      const t = perm[i];
      perm[i] = perm[j];
      perm[j] = t;
    }
    const counts = new Array(27).fill(0);
    let x = enc;
    for (let i = 0; i < 18; i++) {
      const c = x % 5;
      x = (x - c) / 5;
      if (c > 0) counts[perm[Math.floor(i / 9)] * 9 + (i % 9)] = c;
    }
    const melds = [];
    const used = [];
    for (let k = 0; k < meldCount; k++) {
      let idx = -1;
      for (let t = 0; t < 50 && idx < 0; t++) {
        const cand = perm[randInt(rng, 2)] * 9 + randInt(rng, 9);
        if (counts[cand] <= 1 && used.indexOf(cand) < 0) idx = cand;
      }
      if (idx < 0) return null;
      used.push(idx);
      const type = counts[idx] === 0 && rng() < 0.5 ? "gang" : "peng";
      melds.push({ type, tile: indexToTile(idx) });
    }
    if (mode === "ting") {
      const tiles = huTiles(counts, melds);
      if (!inRange(tiles.length, "ting", tier)) return null;
      const handSuits = [...new Set(
        counts.flatMap((c, i) => (c > 0 ? [Math.floor(i / 9)] : []))
      )].sort();
      return {
        mode: "ting",
        hand: sortTiles(tilesFromCounts(counts)),
        melds,
        candidates: handSuits.flatMap((s) =>
          Array.from({ length: 9 }, (_, r) => indexToTile(s * 9 + r))),
        answer: { hu_tiles: tiles },
      };
    }
    const missingSuit = SUITS[perm[2]];
    const options = tingOptions(counts, missingSuit, melds);
    if (!inRange(options.length, "discard", tier)) return null;
    options.sort((a, b) => b.count - a.count);
    return {
      mode: "discard",
      hand: sortTiles(tilesFromCounts(counts)),
      melds,
      missing_suit: missingSuit,
      answer: { best: options.map((d) => d.tile), detail: options },
    };
  }

  // 出题：难度 → 档内胡法数量 → 副露数（权重在该胡法数非空的格上归一）
  // → 洗牌袋抽形。未指定难度按普通档。
  function drawProblem(rng, mode, difficulty) {
    if (!getPoolsSource()) throw new Error("题库未加载：请先引入 pools.js");
    const tier = TIER_N[mode][difficulty] ? difficulty : "normal";
    const letter = mode === "ting" ? "t" : "d";
    for (;;) {
      const n = weightedPick(rng, TIER_N[mode][tier]);
      const mw = {};
      for (let m = 0; m <= 4; m++) {
        if (decodePool(`${letter}_${m}_${n}`)) mw[m] = MELD_WEIGHTS[m];
      }
      const m = weightedPick(rng, mw);
      const key = `${letter}_${m}_${n}`;
      const p = buildProblem(rng, mode, m, bagDraw(rng, key, decodePool(key)), tier);
      if (p) return p; // 配副露掉档时重抽（罕见）
    }
  }

  // 13-3m 张暗牌能胡的所有牌及倍数。胡的牌必须能补全暗牌结构，
  // 所以只在暗牌出现的花色里找；被自家副露占满的牌胡不了。
  function huTiles(counts, melds = []) {
    const extra = meldExtra(melds);
    const handSuits = [...new Set(
      counts.flatMap((c, i) => (c > 0 ? [Math.floor(i / 9)] : []))
    )].sort();
    const result = [];
    for (const s of handSuits) {
      for (let i = s * 9; i < s * 9 + 9; i++) {
        if (counts[i] + extra[i] >= 4) continue;
        counts[i] += 1;
        if (isWin(counts, melds)) {
          const f = fan(counts, melds);
          result.push({ tile: indexToTile(i), fan: f.fan, patterns: f.patterns });
        }
        counts[i] -= 1;
      }
    }
    return result;
  }

  // 已下叫题：13-3m 张暗牌 + 副露，答案 = 能胡哪些牌及倍数。
  function makeTingProblem(rng = Math.random, difficulty = null) {
    return drawProblem(rng, "ting", difficulty);
  }

  // 14-3m 张暗牌中所有打完即下叫的打法及各自听的牌。
  function tingOptions(counts, missingSuit, melds = []) {
    const options = [];
    for (let x = 0; x < 27; x++) {
      if (counts[x] === 0) continue;
      counts[x] -= 1;
      // 先只算向听，命中 0 才算听牌明细
      if (shanten(counts, missingSuit, melds.length) === 0) {
        const u = ukeire(counts, missingSuit, melds);
        // total==0 是形式听牌（听的牌全在自己或副露手里），不算有效下叫
        if (u.total > 0) {
          options.push({ tile: indexToTile(x), waits: u.tiles, count: u.total });
        }
      }
      counts[x] += 1;
    }
    return options;
  }

  // 未下叫题：14-3m 张暗牌 + 副露，答案 = 所有下叫打法及各自听的牌。
  function makeDiscardProblem(rng = Math.random, difficulty = null) {
    return drawProblem(rng, "discard", difficulty);
  }

  // 结账：局中赢家按比例交的茶钱筹码只记比例，真实茶钱现金另结。
  // 结算时把茶钱按人数平分补回每人：输赢 = 筹码 + 茶钱/人数 − 起始。
  // 对账（diff===0，即 Σ筹码+茶钱 = 人数×起始）通过时输赢之和恰为 0。
  // 茶钱除不尽时逐人四舍五入会差一两分钱，deltas 改为按分为单位守恒
  // 分配：每家先取整分（各家余数数学上相同），差的几分从第一家起补齐，
  // 保证金额之和恰为 0 可闭环转账。全程整数运算，无浮点误差。
  function settle(initial, chips, tea) {
    const n = chips.length;
    const share = tea / n;
    const diff = chips.reduce((a, b) => a + b, 0) + tea - initial * n;
    const base = Math.floor((tea * 100) / n);
    let left = tea * 100 - base * n;
    const deltas = chips.map((c) => {
      let cents = (c - initial) * 100 + base;
      if (left > 0) {
        cents += 1;
        left -= 1;
      }
      return cents / 100;
    });
    return { share, deltas, diff };
  }

  return {
    SUITS, SUIT_NAMES,
    tileIndex, indexToTile, formatTile,
    countsFromTiles, tilesFromCounts, sortTiles, suitsIn,
    isWin, fan, shanten, ukeire, decodePool,
    makeTingProblem, makeDiscardProblem, settle,
  };
})();

if (typeof module !== "undefined") module.exports = Majiang;
