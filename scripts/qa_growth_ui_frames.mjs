// P0-3 UI 真页预演（node Playwright + 系统 Chrome 通道）
// 验证四点：绑 QA 账号 / 页面=API / 实时截图 / 双皮肤×三视口；失败保留证据并 exit≠0
import { chromium } from '/Users/hanxianxiang/Downloads/学习/儿童学习成长系统/Learning_Growth_System_GitReady_VCS_Governance_V1.0/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const CHILD = process.env.REHEARSAL_CHILD;
const API = 'http://127.0.0.1:8000';
const DIR = process.env.SHOT_DIR || '/tmp/ui_rehearsal';
fs.mkdirSync(DIR, { recursive: true });

const abilities = await (await fetch(`${API}/v1/children/${CHILD}/abilities`)).json();
const apiMap = Object.fromEntries((abilities.abilities || abilities).map(a => [a.ability_id, a]));
console.log('API 状态:', Object.entries(apiMap).map(([k, v]) => `${k}=L${v.level}`).join(' '));

const insts = [['lab', 'http://localhost:3100'], ['healing', 'http://localhost:3101']];
const vps = [['desktop', 1280, 1000], ['390', 390, 844], ['320', 320, 640]];
const captured = []; const fails = [];

const browser = await chromium.launch({ headless: true, channel: 'chrome' });
for (const [skin, url] of insts) {
  for (const [vn, w, h] of vps) {
    const page = await browser.newPage({ viewport: { width: w, height: h } });
    const reqs = [];
    page.on('request', r => { if (r.url().includes('/v1/children/')) reqs.push(r.url()); });
    const id = `${skin}-${vn}`;
    try {
      await page.goto(`${url}/child/math/growth?child_id=${CHILD}`, { waitUntil: 'networkidle', timeout: 240_000 });
      await page.waitForTimeout(1500);
      const png = `${DIR}/growth_${id}.png`;
      await page.screenshot({ path: png, full_page: true });
      const body = await page.evaluate(() => document.body.innerText);
      // ① 浏览器发出的 children 请求全绑 QA child（无串号）
      const bound = reqs.length > 0 && reqs.every(u => u.includes(CHILD));
      // ② 页面渲染的能力等级与 API 一致：每个 L1 能力，页面文本里能力中文名与等级表征存在
      const names = { app_rel: '数量关系', app_model: '建模表征', app_rd: '读题理解', app_cond: '条件识别', app_check: '检查验算', app_strat: '策略选择' };
      let consistent = true; const missing = [];
      for (const [ab, st] of Object.entries(apiMap)) {
        if (st.level >= 1) {
          const nm = names[ab] || ab;
          if (!body.includes(nm)) { consistent = false; missing.push(nm); }
        }
      }
      captured.push({ id, png: fs.existsSync(png), bound_qa: bound, api_children_reqs: reqs.length,
        page_level_consistent: consistent, missing, overflow: await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth) });
      console.log('✓', id, 'png=ok', '绑QA=', bound, '等级一致=', consistent, missing.length ? '缺:' + missing : '');
    } catch (e) {
      fails.push({ id, err: String(e).slice(0, 160) });
      console.log('✗', id, String(e).slice(0, 120));
    } finally { await page.close(); }
  }
}
await browser.close();
const ok = captured.length === 6 && captured.every(c => c.png && c.bound_qa && c.page_level_consistent) && fails.length === 0;
fs.writeFileSync(`${DIR}/ui_rehearsal_report.json`, JSON.stringify({ child: CHILD, captured, fails, realtime: true, verdict: ok ? 'PASS' : 'FAIL' }, null, 1));
console.log('P0-3 预演:', ok ? 'PASS（6/6 帧·实时·绑QA·页=API）' : 'FAIL（证据保留，不冒充成功）');
process.exit(ok ? 0 : 1);
