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

Page({
  data: {
    mode: "settle",
    difficulty: "normal",
    hand: [],
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
    sRows: [],
    sCheck: "",
    sBalanced: true,
  },

  onLoad() {
    if (this.data.mode !== "settle") this.newProblem();
  },

  switchMode(e) {
    const mode = e.currentTarget.dataset.mode;
    this.setData({ mode });
    if (mode !== "settle") this.newProblem();
  },

  setDifficulty(e) {
    this.setData({ difficulty: e.currentTarget.dataset.diff });
    this.newProblem();
  },

  newProblem() {
    const { mode, difficulty } = this.data;
    const p = mode === "ting"
      ? Majiang.makeTingProblem(Math.random, difficulty)
      : Majiang.makeDiscardProblem(Math.random, difficulty);
    this.problem = p;
    this.discardPicks = [];
    this.setData({
      hand: p.hand.map(deco),
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
  sCountInput(e) {
    const n = Number(e.detail.value);
    const patch = { sCount: e.detail.value };
    if (n >= 2 && n <= 8) {
      // 人数变化时重建筹码数组，保留已填的值
      const chips = [];
      for (let i = 0; i < n; i++) chips.push(this.data.sChips[i] || "");
      patch.sChips = chips;
    }
    this.setData(patch);
  },

  sInitInput(e) {
    this.setData({ sInit: e.detail.value });
  },

  sTeaInput(e) {
    this.setData({ sTea: e.detail.value });
  },

  sChipInput(e) {
    const chips = this.data.sChips.slice();
    chips[e.currentTarget.dataset.i] = e.detail.value;
    this.setData({ sChips: chips });
  },

  doSettle() {
    const money = (x) => String(Math.round(x * 100) / 100);
    const init = Number(this.data.sInit);
    const tea = Number(this.data.sTea);
    const chips = this.data.sChips.map((v) =>
      String(v).trim() === "" ? NaN : Number(v));
    if (!isFinite(init) || !isFinite(tea) || chips.some((c) => !isFinite(c))) {
      this.setData({ sCheck: "请把所有数字填完整。", sBalanced: false, sRows: [] });
      return;
    }
    const n = chips.length;
    const r = Majiang.settle(init, chips, tea);
    const total = chips.reduce((a, b) => a + b, 0) + tea;
    this.setData({
      sBalanced: r.diff === 0,
      sCheck: r.diff === 0
        ? `对账正确：${n} 家筹码 + 茶钱 = ${init * n}。`
        : `对不上：${n} 家筹码 + 茶钱 = ${total}，应为 ${n} × ${init} = ${init * n}，` +
          `差 ${money(Math.abs(r.diff))}，请核对。`,
      sShare: money(r.share),
      sRows: chips.map((c, i) => {
        const d = Math.round(r.deltas[i] * 100) / 100;
        return {
          name: `玩家${i + 1}`,
          chips: c,
          cls: d > 0 ? "recv" : d < 0 ? "pay" : "",
          text: d > 0 ? `收 ${money(d)} 元` : d < 0 ? `付 ${money(-d)} 元` : "不输不赢",
        };
      }),
    });
  },
});
