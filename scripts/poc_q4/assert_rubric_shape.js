// 结构断言：机器可读字段齐全（G2 要求 evidence_pointer 可验证）
module.exports = (output) => {
  try {
    const j = JSON.parse(output);
    const ok = ["rvid","independent_answer","confidence","risk_code","evidence_pointer","recommendation"]
      .every(k => k in j);
    return { pass: ok, score: ok ? 1 : 0, reason: ok ? "schema ok" : "缺字段" };
  } catch (e) { return { pass: false, score: 0, reason: "非 JSON" }; }
};
