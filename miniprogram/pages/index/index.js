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
    mode: "ting",
    difficulty: "normal",
    hand: [],
    candidateRows: [],
    picks: [],
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
    this.newProblem();
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
    this.setData({
      hand: p.hand.map(deco),
      candidateRows: mode === "ting" ? rowsBySuit(p.candidates) : [],
      missingName: mode === "discard" ? Majiang.SUIT_NAMES[p.missing_suit] : "",
      picks: [],
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

  // 点手牌：把该牌加入/移出下方副本区（同种牌只记一次）
  discardTap(e) {
    if (this.data.answered || this.data.mode !== "discard") return;
    this.togglePick(this.data.hand[e.currentTarget.dataset.i].tile);
  },

  // 点副本：取消该选择
  pickTap(e) {
    if (this.data.answered) return;
    this.togglePick(this.data.picks[e.currentTarget.dataset.i].tile);
  },

  togglePick(tile) {
    let tiles = this.data.picks.map((p) => p.tile);
    tiles = tiles.includes(tile)
      ? tiles.filter((t) => t !== tile)
      : tiles.concat(tile);
    const sel = new Set(tiles);
    this.setData({
      picks: Majiang.sortTiles(tiles).map(deco),
      hand: this.data.hand.map((h) => ({ ...h, sel: sel.has(h.tile) })),
    });
  },

  judgeDiscard() {
    const correct = new Set(this.problem.answer.best);
    const chosen = new Set(this.data.picks.map((p) => p.tile));
    const ok = correct.size === chosen.size && [...correct].every((t) => chosen.has(t));
    const picks = this.data.picks.map((p) => ({
      ...p, mark: correct.has(p.tile) ? "good" : "bad",
    }));
    // 漏选的补在副本区末尾标黄
    Majiang.sortTiles([...correct].filter((t) => !chosen.has(t))).forEach((t) => {
      picks.push({ ...deco(t), mark: "missed" });
    });
    this.setData({
      answered: true,
      picks,
      verdict: ok ? "正确！" : "不对，看看漏了或多选了哪些。",
      verdictOk: ok,
      discardRows: this.problem.answer.detail.map((d) => ({
        text: Majiang.formatTile(d.tile),
        waits: d.waits.map(Majiang.formatTile).join(" "),
        count: d.count,
      })),
      footnote: "枚数按每种剩 4 张减去手中张数估算；打其他牌都不能下叫。",
    });
  },

  next() {
    // 选了牌却没提交就点下一题：先判定，避免误以为没有反馈
    if (!this.data.answered
        && ((this.data.mode === "ting"
             && this.data.candidateRows.some((row) => row.some((c) => c.sel)))
            || (this.data.mode === "discard" && this.data.picks.length > 0))) {
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
