const Majiang = require("../../majiang.js");

// WXML 里不能调用函数，牌的显示文本、牌面数据和花色 class 在 setData 前算好
function deco(tile) {
  const face = Majiang.tileFace(tile);
  return {
    tile,
    text: Majiang.formatTile(tile),
    suit: tile[1],
    face,
    rowsClass: face.rows ? `rows${face.rows.length}` : "",
    sel: false,
    mark: "",
  };
}

Page({
  data: {
    mode: "ting",
    hand: [],
    candidates: [],
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

  newProblem() {
    const mode = this.data.mode;
    const p = mode === "ting" ? Majiang.makeTingProblem() : Majiang.makeDiscardProblem();
    this.problem = p;
    this.setData({
      hand: p.hand.map(deco),
      candidates: mode === "ting" ? p.candidates.map(deco) : [],
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
    const i = e.currentTarget.dataset.i;
    this.setData({ [`candidates[${i}].sel`]: !this.data.candidates[i].sel });
  },

  submit() {
    if (this.data.answered || this.data.mode !== "ting") return;
    const answer = this.problem.answer.hu_tiles;
    const correct = new Set(answer.map((h) => h.tile));
    const chosen = new Set(this.data.candidates.filter((c) => c.sel).map((c) => c.tile));
    const ok = correct.size === chosen.size && [...correct].every((t) => chosen.has(t));
    const candidates = this.data.candidates.map((c) => {
      let mark = "";
      if (correct.has(c.tile) && chosen.has(c.tile)) mark = "good";
      else if (!correct.has(c.tile) && chosen.has(c.tile)) mark = "bad";
      else if (correct.has(c.tile)) mark = "missed";
      return { ...c, mark };
    });
    this.setData({
      answered: true,
      candidates,
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
        && this.data.candidates.some((c) => c.sel)) {
      this.submit();
      return;
    }
    this.newProblem();
  },
});
