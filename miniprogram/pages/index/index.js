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
    missingName: "",
    answered: false,
    verdict: "",
    verdictOk: false,
    tingRows: [],
    discardRows: [],
    footnote: "",
  },

  onLoad() {
    this.newProblem();
  },

  switchMode(e) {
    this.setData({ mode: e.currentTarget.dataset.mode });
    this.newProblem();
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
    if (this.data.answered || this.data.mode !== "ting") return;
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

  discardTap(e) {
    if (this.data.answered || this.data.mode !== "discard") return;
    const tile = this.data.hand[e.currentTarget.dataset.i].tile;
    const best = new Set(this.problem.answer.best);
    const ok = best.has(tile);
    this.setData({
      answered: true,
      verdict: ok
        ? `正确！打 ${Majiang.formatTile(tile)} 即下叫。`
        : `打 ${Majiang.formatTile(tile)} 不能下叫。能下叫的打法：` +
          this.problem.answer.best.map(Majiang.formatTile).join(" / "),
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
    if (!this.data.answered && this.data.mode === "ting"
        && this.data.candidateRows.some((row) => row.some((c) => c.sel))) {
      this.submit();
      return;
    }
    this.newProblem();
  },
});
