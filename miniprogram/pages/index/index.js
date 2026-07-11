const Majiang = require("../../majiang.js");

// WXML 里不能调用函数，牌的显示文本和图片路径在 setData 前算好
function deco(tile) {
  return {
    tile,
    text: Majiang.formatTile(tile),
    suit: tile[1],
    src: `/assets/tiles/${tile[1]}${tile[0]}.png`,
    sel: false,
    mark: "",
  };
}

// 两个花色分成两行
function rowsBySuit(tiles) {
  const rows = [];
  for (const s of "msp") {
    const row = tiles.filter((t) => t[1] === s).map(deco);
    if (row.length > 0) rows.push(row);
  }
  return rows;
}

// 副露区显示数据：每组标注 碰/明杠/暗杠，全部正面显示（自己视角不盖牌）
function buildMelds(melds) {
  const names = { peng: "碰", gang: "明杠", angang: "暗杠" };
  return melds.map((meld) => ({
    label: names[meld.type],
    tiles: Array.from({ length: meld.type === "peng" ? 3 : 4 },
      () => `/assets/tiles/${meld.tile[1]}${meld.tile[0]}.png`),
  }));
}

function generate(mode, difficulty) {
  return mode === "ting"
    ? Majiang.makeTingProblem(Math.random, difficulty)
    : Majiang.makeDiscardProblem(Math.random, difficulty);
}

Page({
  data: {
    mode: "settle",
    difficulty: "normal",
    hand: [],
    melds: [],
    candidateRows: [],
    rows: [],
    missingName: "",
    answered: false,
    verdict: "",
    verdictOk: false,
    tingRows: [],
    discardRows: [],
    footnote: "",
    sCount: "4",
    sInit: "100",
    sChips: ["", "", "", ""],
    sTea: "0",
    sShare: "0",
    sRes: [],
    sCheck: "",
    sBalanced: true,
  },

  onLoad() {
    if (this.data.mode !== "settle") this.newProblem();
  },

  switchMode(e) {
    const mode = e.currentTarget.dataset.mode;
    // 判定和结果区域在模式区块之外，切页（尤其切到结账）要清掉旧答案
    this.setData({
      mode,
      answered: false,
      verdict: "",
      verdictOk: false,
      tingRows: [],
      discardRows: [],
      footnote: "",
    });
    if (mode !== "settle") this.newProblem();
  },

  setDifficulty(e) {
    this.setData({ difficulty: e.currentTarget.dataset.diff });
    this.newProblem();
  },

  // 出完当前题就在后台把下一题先算好，点"下一题"零等待；
  // 切换模式或难度后缓存对不上号，自然失效重新生成
  schedulePrefetch() {
    const { mode, difficulty } = this.data;
    setTimeout(() => {
      if (this.data.mode === mode && this.data.difficulty === difficulty
          && !(this.prefetch && this.prefetch.mode === mode
               && this.prefetch.difficulty === difficulty)) {
        this.prefetch = { mode, difficulty, problem: generate(mode, difficulty) };
      }
    }, 50);
  },

  newProblem() {
    const { mode, difficulty } = this.data;
    let p;
    if (this.prefetch && this.prefetch.mode === mode
        && this.prefetch.difficulty === difficulty) {
      p = this.prefetch.problem;
      this.prefetch = null;
    } else {
      p = generate(mode, difficulty);
    }
    this.problem = p;
    this.discardPicks = [];
    this.setData({
      hand: p.hand.map(deco),
      melds: buildMelds(p.melds),
      candidateRows: mode === "ting" ? rowsBySuit(p.candidates) : [],
      missingName: mode === "discard" ? Majiang.SUIT_NAMES[p.missing_suit] : "",
      rows: mode === "discard" ? this.buildDiscardRows(false) : [],
      answered: false,
      verdict: "",
      verdictOk: false,
      tingRows: [],
      discardRows: [],
      footnote: "",
    });
    this.schedulePrefetch();
  },

  toggleTile(e) {
    if (this.data.answered) return;
    const { r, i } = e.currentTarget.dataset;
    this.setData({
      [`candidateRows[${r}][${i}].sel`]: !this.data.candidateRows[r][i].sel,
    });
  },

  submit() {
    if (this.data.answered) return;
    if (this.data.mode === "ting") this.judgeTing();
    else if (this.data.mode === "discard") this.judgeDiscard();
  },

  judgeTing() {
    const answer = this.problem.answer.hu_tiles;
    const correct = new Set(answer.map((h) => h.tile));
    const flat = [].concat(...this.data.candidateRows);
    const chosen = new Set(flat.filter((c) => c.sel).map((c) => c.tile));
    const ok = correct.size === chosen.size && [...correct].every((t) => chosen.has(t));
    const candidateRows = this.data.candidateRows.map((row) =>
      row.map((c) => {
        let mark = "";
        if (correct.has(c.tile) && chosen.has(c.tile)) mark = "good";
        else if (!correct.has(c.tile) && chosen.has(c.tile)) mark = "bad";
        else if (correct.has(c.tile)) mark = "missed";
        return { ...c, mark };
      })
    );
    this.setData({
      answered: true,
      candidateRows,
      verdict: ok ? "正确！" : "不对，看看漏了或多选了哪些。",
      verdictOk: ok,
      tingRows: answer.map((h) => ({
        text: Majiang.formatTile(h.tile),
        fan: h.fan,
        patterns: h.patterns.join("、"),
      })),
      footnote: "倍数不含自摸、杠上花等加成。",
    });
  },

  // 已选 n 种打法就显示 n+1 排手牌，每排点选一张；点该排已选的牌取消整排，
  // 点其他牌换选（与其他排重复的忽略）；判定后漏选的打法补成新排标黄
  buildDiscardRows(answered) {
    const picks = this.discardPicks;
    const correct = answered ? new Set(this.problem.answer.best) : null;
    const rows = picks.map((t) => ({ pick: t, missed: false }));
    if (!answered) rows.push({ pick: null, missed: false });
    else Majiang.sortTiles(this.problem.answer.best.filter((t) => !picks.includes(t)))
      .forEach((t) => rows.push({ pick: t, missed: true }));
    return rows.map((r, i) => {
      let marked = false;
      const tiles = this.problem.hand.map((t) => {
        const d = deco(t);
        if (!marked && t === r.pick) {
          marked = true;
          if (!answered) d.sel = true;
          else d.mark = r.missed ? "missed" : correct.has(t) ? "good" : "bad";
        }
        return d;
      });
      const label = r.pick === null
        ? (i === 0 ? "点选一张打出后能下叫的牌：" : `第 ${i + 1} 种打法（点选一张，或直接提交）：`)
        : r.missed ? "漏选的打法：" : `第 ${i + 1} 种打法：`;
      return { label, tiles };
    });
  },

  discardTap(e) {
    if (this.data.answered || this.data.mode !== "discard") return;
    const { r, i } = e.currentTarget.dataset;
    const t = this.problem.hand[i];
    const picks = this.discardPicks;
    if (r < picks.length) {
      if (picks[r] === t) picks.splice(r, 1);
      else if (!picks.includes(t)) picks[r] = t;
    } else if (!picks.includes(t)) {
      picks.push(t);
    }
    this.setData({ rows: this.buildDiscardRows(false) });
  },

  judgeDiscard() {
    const correct = new Set(this.problem.answer.best);
    const chosen = new Set(this.discardPicks);
    const ok = correct.size === chosen.size && [...correct].every((t) => chosen.has(t));
    this.setData({
      answered: true,
      rows: this.buildDiscardRows(true),
      verdict: ok ? "正确！" : "不对，看看漏了或多选了哪些。",
      verdictOk: ok,
      discardRows: this.problem.answer.detail.map((d) => ({
        text: Majiang.formatTile(d.tile),
        waits: d.waits.map(Majiang.formatTile).join(" "),
      })),
      footnote: "打其他牌都不能下叫。",
    });
  },

  next() {
    // 选了牌却没提交就点下一题：先判定，避免误以为没有反馈
    if (!this.data.answered
        && ((this.data.mode === "ting"
             && this.data.candidateRows.some((row) => row.some((c) => c.sel)))
            || (this.data.mode === "discard" && this.discardPicks.length > 0))) {
      this.submit();
      return;
    }
    this.newProblem();
  },

  // ---- 结账 ----
  // 任何输入变化都清掉上次结算结果，避免显示过期数字
  sCountInput(e) {
    const n = Number(e.detail.value);
    const patch = { sCount: e.detail.value, sRes: [], sCheck: "", sBalanced: true };
    if (Number.isInteger(n) && n >= 2 && n <= 8) {
      // 人数变化时重建筹码数组，保留已填的值
      const chips = [];
      for (let i = 0; i < n; i++) chips.push(this.data.sChips[i] || "");
      patch.sChips = chips;
    }
    this.setData(patch);
  },

  sInitInput(e) {
    this.setData({ sInit: e.detail.value, sRes: [], sCheck: "", sBalanced: true });
  },

  sTeaInput(e) {
    this.setData({ sTea: e.detail.value, sRes: [], sCheck: "", sBalanced: true });
  },

  sChipInput(e) {
    const chips = this.data.sChips.slice();
    chips[e.currentTarget.dataset.i] = e.detail.value;
    this.setData({ sChips: chips, sRes: [], sCheck: "", sBalanced: true });
  },

  doSettle() {
    const money = (x) => String(Math.round(x * 100) / 100);
    const fail = (msg) => this.setData({ sCheck: msg, sBalanced: false, sRes: [] });
    const cnt = Number(this.data.sCount);
    if (!Number.isInteger(cnt) || cnt < 2 || cnt > 8) return fail("人数需为 2-8 的整数。");
    const init = String(this.data.sInit).trim() === "" ? NaN : Number(this.data.sInit);
    if (!Number.isInteger(init) || init <= 0) return fail("起始筹码需为正整数。");
    const chips = this.data.sChips.map((v) =>
      String(v).trim() === "" ? NaN : Number(v));
    if (chips.some((c) => !Number.isInteger(c) || c < 0))
      return fail("每家终局筹码需为非负整数，请填完整。");
    const tea = String(this.data.sTea).trim() === "" ? NaN : Number(this.data.sTea);
    if (!Number.isInteger(tea) || tea < 0) return fail("茶钱需为非负整数。");

    const n = chips.length;
    const r = Majiang.settle(init, chips, tea);
    if (r.diff !== 0) {
      const total = chips.reduce((a, b) => a + b, 0) + tea;
      return fail(`对不上：${n} 家筹码 + 茶钱 = ${total}，` +
        `应为 ${n} × ${init} = ${init * n}，差 ${money(Math.abs(r.diff))}，请核对后再结算。`);
    }
    this.setData({
      sBalanced: true,
      sCheck: `对账正确：${n} 家筹码 + 茶钱 = ${init * n}。`,
      sShare: money(r.share),
      sRes: r.deltas.map((x) => {
        const d = Math.round(x * 100) / 100;
        return {
          cls: d > 0 ? "recv" : d < 0 ? "pay" : "",
          text: d > 0 ? `收 ${money(d)} 元` : d < 0 ? `付 ${money(-d)} 元` : "不输不赢",
        };
      }),
    });
  },
});
