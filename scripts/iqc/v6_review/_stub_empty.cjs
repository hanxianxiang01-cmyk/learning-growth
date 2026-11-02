/**
 * 临时假后端：只为验证「全新游客」的首页/成长页空状态（0/7、树苗、七行尚待探索）。
 * mock 模式永远返回 7 项有证据的能力，空状态在 mock 里根本跑不到——
 * 那是「判据没覆盖被核系统的输入边界」，所以单独起一个只会返回空数据的桩。
 *
 *   POST /v1/guest/bootstrap → 201 + Cookie + activity
 *   GET  /v1/guest/me        → 无 Cookie 401，有则 200
 *   GET  /v1/children/:id/abilities → []（一条记录都没有）
 * 其余一律 404，多一个端点就多一个假成功的机会。
 */
const http = require("node:http");

const PORT = Number(process.env.STUB_PORT || 8099);
const children = new Map();
let n = 0;
const today = new Date().toISOString().slice(0, 10);

const cors = (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", req.headers.origin || "*");
  res.setHeader("Access-Control-Allow-Credentials", "true");
  res.setHeader("Access-Control-Allow-Headers", "content-type");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
};
const token = (req) => (req.headers.cookie || "").match(/guest_session=([^;]+)/)?.[1] ?? null;
const json = (res, code, body) => { res.writeHead(code, { "content-type": "application/json" }); res.end(JSON.stringify(body)); };
const activity = { date: today, timezone: "Asia/Shanghai", answered_today: 0 };

http.createServer((req, res) => {
  cors(req, res);
  if (req.method === "OPTIONS") { res.writeHead(204); res.end(); return; }
  const p = new URL(req.url, `http://127.0.0.1:${PORT}`).pathname;

  if (p === "/v1/guest/bootstrap" && req.method === "POST") {
    const t = token(req);
    if (t && children.has(t)) return json(res, 200, { child_id: children.get(t), is_new: false, expires_at: "2099-01-01T00:00:00Z", retention_days: 7, activity });
    n += 1;
    const tok = `tok-${n}`;
    const id = `22222222-0000-0000-0000-00000000000${n}`.slice(-36);
    children.set(tok, id);
    res.setHeader("Set-Cookie", `guest_session=${tok}; HttpOnly; SameSite=Lax; Path=/`);
    return json(res, 201, { child_id: id, is_new: true, expires_at: "2099-01-01T00:00:00Z", retention_days: 7, activity });
  }
  if (p === "/v1/guest/me") {
    const t = token(req);
    if (!t || !children.has(t)) return json(res, 401, { detail: { code: "LE-4010", message: "guest session missing" } });
    return json(res, 200, { child_id: children.get(t), expires_at: "2099-01-01T00:00:00Z", retention_days: 7, activity });
  }
  if (/^\/v1\/children\/[^/]+\/abilities$/.test(p)) return json(res, 200, []);
  if (/^\/v1\/children\/[^/]+\/profile$/.test(p)) {
    return json(res, 200, { child_id: children.get(token(req) || ""), grade: "2", active_abilities: [], strengths: [], developing: [], observations: [] });
  }
  return json(res, 404, { detail: { code: "NOT_IMPL", message: p } });
}).listen(PORT, "127.0.0.1", () => console.log(`empty stub on ${PORT}`));
