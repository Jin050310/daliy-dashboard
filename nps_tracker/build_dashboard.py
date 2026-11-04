"""대시보드 HTML을 만든다.

    python build_dashboard.py

입력: data/daily_value.csv (step7), data/latest_holdings.csv (step7), data/monthly_check.csv (step8)
출력: site/index.html (데이터를 안에 담은 파일 하나. GitHub Pages로 그대로 배포한다)
"""
import json
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd

import config

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

TOP_N = 15  # 표에 보여 줄 상위 종목 수
KST = timezone(timedelta(hours=9))


def main() -> None:
    for f in (config.DAILY_VALUE_CSV, config.LATEST_HOLDINGS_CSV, config.MONTHLY_CHECK_CSV):
        if not f.exists():
            raise SystemExit(f"파일이 없습니다: {f} (먼저 step7, step8을 실행하세요)")
    v = pd.read_csv(config.DAILY_VALUE_CSV, dtype={"basDt": str}, encoding="utf-8-sig")
    h = pd.read_csv(config.LATEST_HOLDINGS_CSV, dtype={"종목코드": str}, encoding="utf-8-sig")
    m = pd.read_csv(config.MONTHLY_CHECK_CSV, dtype={"월": str, "기준거래일": str}, encoding="utf-8-sig")

    data = {
        "updated": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "daily": [[d, round(x, 3)] for d, x in zip(v["basDt"], v["평가액_조"])],
        "stale": int(v["종가고정_종목수"].iloc[-1]),
        "official": [
            {"ym": r["월"], "date": r["기준거래일"], "tracked": r["추적값_조"], "official": r["공시값_조"],
             "cover": r["커버율_%"], "gap": r["기준대비_추가차이_%p"], "trust": r["신뢰"], "src": r["출처"]}
            for _, r in m.iterrows()
        ],
        "top": [
            {"name": r["종목명"], "code": r["종목코드"], "base": r["기준일_억"], "now": r["최근일_억"],
             "chg": r["변화율_%"], "w": r["최근_비중_%"], "stale": bool(r["종가고정"])}
            for _, r in h.head(TOP_N).iterrows()
        ],
        "n_holdings": int(len(h)),
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    config.SITE_DIR.mkdir(parents=True, exist_ok=True)
    out = config.SITE_DIR / "index.html"
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")
    print(f"저장: {out} (최근일 {v['basDt'].iloc[-1]}, {v['평가액_조'].iloc[-1]:.2f}조 원)")


TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>국민연금 국내주식 추적</title>
<meta name="description" content="국민연금 2025년 말 공시 국내주식 보유분을 매일 종가로 평가한 금액">
<style>
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --border: rgba(11,11,11,0.10);
  --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7;
  --s1: #2a78d6; --s2: #eb6834;
  --up: #d03b3b; --down: #2a78d6;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --border: rgba(255,255,255,0.10);
    --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835;
    --s1: #3987e5; --s2: #d95926;
    --up: #e66767; --down: #3987e5;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --border: rgba(255,255,255,0.10);
  --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
  --grid: #2c2c2a; --axis: #383835;
  --s1: #3987e5; --s2: #d95926;
  --up: #e66767; --down: #3987e5;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink);
  font: 15px/1.55 system-ui, -apple-system, "Segoe UI", "Malgun Gothic", sans-serif; }
main { max-width: 1040px; margin: 0 auto; padding: 28px 16px 48px; }
header h1 { font-size: 22px; margin: 0 0 4px; letter-spacing: -0.01em; }
header p { margin: 0; color: var(--ink-2); font-size: 14px; }
.badge { display: inline-block; margin-top: 10px; padding: 3px 10px; border-radius: 999px;
  border: 1px solid var(--border); color: var(--ink-2); font-size: 12.5px; background: var(--surface); }
.tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 22px 0; }
.tile { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; }
.tile .k { color: var(--ink-2); font-size: 13px; }
.tile .v { font-size: 26px; font-weight: 650; margin-top: 2px; letter-spacing: -0.01em; }
.tile .s { color: var(--muted); font-size: 12.5px; margin-top: 2px; }
.up { color: var(--up); } .down { color: var(--down); }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px; margin-bottom: 16px; }
.card h2 { font-size: 16px; margin: 0 0 4px; }
.card .sub { color: var(--ink-2); font-size: 13px; margin: 0 0 12px; }
.controls { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-bottom: 8px; }
.controls button { font: inherit; font-size: 13px; padding: 4px 12px; border-radius: 8px; cursor: pointer;
  border: 1px solid var(--border); background: transparent; color: var(--ink-2); }
.controls button[aria-pressed="true"] { background: var(--ink); color: var(--surface); border-color: var(--ink); }
.legend { display: flex; gap: 16px; margin-left: auto; font-size: 12.5px; color: var(--ink-2); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.key-line { width: 16px; height: 2px; background: var(--s1); border-radius: 1px; }
.key-dot { width: 9px; height: 9px; border-radius: 50%; background: var(--s2); box-shadow: 0 0 0 2px var(--surface); }
.chart { position: relative; }
.chart svg { display: block; width: 100%; height: 320px; }
.chart text { fill: var(--muted); font-size: 11.5px; font-variant-numeric: tabular-nums; }
.tip { position: absolute; pointer-events: none; background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; padding: 8px 10px; font-size: 12.5px; box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  white-space: nowrap; display: none; }
.tip .d { color: var(--muted); margin-bottom: 4px; }
.tip .row { display: flex; align-items: center; gap: 8px; }
.tip .row b { font-weight: 650; }
.tip .row i { width: 12px; height: 2px; display: inline-block; }
.tip .row span { color: var(--ink-2); }
table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
th, td { padding: 7px 8px; text-align: right; border-bottom: 1px solid var(--grid); font-variant-numeric: tabular-nums; white-space: nowrap; }
th { color: var(--ink-2); font-weight: 550; font-size: 12.5px; }
th:first-child, td:first-child { text-align: left; }
.tbl { overflow-x: auto; }
details { margin-top: 10px; } summary { cursor: pointer; color: var(--ink-2); font-size: 13px; }
.notes { color: var(--ink-2); font-size: 13.5px; } .notes li { margin: 4px 0; }
.muted { color: var(--muted); }
footer { color: var(--muted); font-size: 12.5px; margin-top: 18px; }
@media (max-width: 720px) {
  .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .tile .v { font-size: 22px; }
  .legend { margin-left: 0; width: 100%; }
  .chart svg { height: 260px; }
  table { font-size: 13px; }
  th, td { padding: 6px 6px; }
}
</style>
</head>
<body>
<main>
  <header>
    <h1>국민연금 국내주식 추적</h1>
    <p>국민연금이 공시한 2025년 말 국내주식 보유분을 매일 종가로 평가한 금액입니다.</p>
    <span class="badge" id="badge"></span>
  </header>

  <section class="tiles" id="tiles" aria-label="핵심 지표"></section>

  <section class="card">
    <h2>일별 평가액</h2>
    <p class="sub">단위: 조 원 · 점은 국민연금이 공시한 월말 국내주식 평가액</p>
    <div class="controls" role="group" aria-label="기간">
      <button data-range="21">1개월</button>
      <button data-range="63">3개월</button>
      <button data-range="126">6개월</button>
      <button data-range="0" aria-pressed="true">전체</button>
      <div class="legend">
        <span><i class="key-line"></i>추적값 (2025년 말 보유분)</span>
        <span><i class="key-dot"></i>국민연금 공시 월말값</span>
      </div>
    </div>
    <div class="chart" id="chart"><svg id="svg" role="img" aria-label="일별 평가액 추이"></svg><div class="tip" id="tip"></div></div>
    <details><summary>표로 보기</summary><div class="tbl"><table id="dailyTable"></table></div></details>
  </section>

  <section class="card">
    <h2>평가액 상위 종목</h2>
    <p class="sub" id="topSub"></p>
    <div class="tbl"><table id="topTable"></table></div>
  </section>

  <section class="card">
    <h2>공시값과 비교</h2>
    <p class="sub">2025년 말 보유분을 그대로 들고 있다고 가정한 값과 실제 공시값의 차이입니다. 기준일 차이(커버율)에서 벗어난 만큼이 그 뒤 매매 효과의 대략적인 크기입니다.</p>
    <div class="tbl"><table id="checkTable"></table></div>
  </section>

  <section class="card notes">
    <h2>읽을 때 주의할 점</h2>
    <ul>
      <li>국민연금의 <b>실제 오늘 보유분이 아닙니다.</b> 2025년 말 이후의 매매는 반영하지 않습니다.</li>
      <li>국내주식만 다루며 기금 전체 자산이 아닙니다. 공시 종목 중 매핑된 종목(평가액 기준 99.98%)만 포함합니다.</li>
      <li>종가는 다음 영업일 오후에 공개되므로 하루 늦게 반영됩니다. 매 평일 오후에 자동으로 갱신됩니다.</li>
      <li>액면분할·병합·무상증자와 주식 교부 합병은 보유 주식 수에 반영했습니다. 유상증자 참여 여부는 알 수 없어 반영하지 않습니다.</li>
      <li>상장폐지·공개매수 등으로 거래가 끊긴 종목은 마지막 종가로 고정합니다.</li>
    </ul>
  </section>

  <footer id="footer"></footer>
</main>

<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  const D = JSON.parse(document.getElementById('data').textContent);
  const daily = D.daily.map(([d, v]) => ({ d, v, t: Date.UTC(+d.slice(0, 4), +d.slice(4, 6) - 1, +d.slice(6, 8)) }));
  const official = D.official.filter(o => o.trust === '공식');
  const fmtDate = d => `${d.slice(0, 4)}.${d.slice(4, 6)}.${d.slice(6, 8)}`;
  const jo = v => v.toLocaleString('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const pct = v => (v > 0 ? '+' : '') + v.toFixed(2) + '%';
  const cls = v => v > 0 ? 'up' : v < 0 ? 'down' : '';
  const arrow = v => v > 0 ? '▲ ' : v < 0 ? '▼ ' : '';
  const el = (tag, attrs = {}, text) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (text !== undefined) e.textContent = text;
    return e;
  };

  // 머리말·핵심 지표
  const last = daily[daily.length - 1], prev = daily[daily.length - 2], base = daily[0];
  const peak = daily.reduce((a, b) => (b.v > a.v ? b : a));
  document.getElementById('badge').textContent = `기준일 ${fmtDate(last.d)} 종가 · 업데이트 ${D.updated} KST`;
  const tiles = [
    ['최근 평가액', `${jo(last.v)}조 원`, fmtDate(last.d), ''],
    ['전일 대비', arrow(last.v - prev.v) + pct((last.v / prev.v - 1) * 100), `${(last.v - prev.v > 0 ? '+' : '')}${jo(last.v - prev.v)}조 원`, cls(last.v - prev.v)],
    ['2025년 말 대비', arrow(last.v - base.v) + pct((last.v / base.v - 1) * 100), `기준 ${jo(base.v)}조 원 (${fmtDate(base.d)})`, cls(last.v - base.v)],
    ['기간 중 최고', `${jo(peak.v)}조 원`, fmtDate(peak.d), ''],
  ];
  const tilesEl = document.getElementById('tiles');
  for (const [k, v, s, c] of tiles) {
    const t = el('div', { class: 'tile' });
    t.append(el('div', { class: 'k' }, k), el('div', { class: 'v ' + c }, v), el('div', { class: 's' }, s));
    tilesEl.append(t);
  }

  // 차트
  const svg = document.getElementById('svg'), tip = document.getElementById('tip'), box = document.getElementById('chart');
  const NS = 'http://www.w3.org/2000/svg';
  const sv = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };
  let range = 0;

  function niceStep(span) {
    const raw = span / 5, p = Math.pow(10, Math.floor(Math.log10(raw))), n = raw / p;
    return (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * p;
  }

  function draw() {
    const pts = range ? daily.slice(-range - 1) : daily;
    const offs = official.map(o => ({ ...o, t: Date.UTC(+o.date.slice(0, 4), +o.date.slice(4, 6) - 1, +o.date.slice(6, 8)) }))
      .filter(o => o.t >= pts[0].t && o.t <= pts[pts.length - 1].t);
    const W = svg.clientWidth, H = svg.clientHeight, L = 44, R = 14, T = 12, B = 26;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.replaceChildren();
    const vals = pts.map(p => p.v).concat(offs.map(o => o.official));
    let lo = Math.min(...vals), hi = Math.max(...vals);
    const step = niceStep(hi - lo || 1);
    lo = Math.floor(lo / step) * step; hi = Math.ceil(hi / step) * step;
    const t0 = pts[0].t, t1 = pts[pts.length - 1].t;
    const x = t => L + (W - L - R) * (t - t0) / ((t1 - t0) || 1);
    const y = v => T + (H - T - B) * (1 - (v - lo) / ((hi - lo) || 1));

    for (let v = lo; v <= hi + 1e-9; v += step) {
      svg.append(sv('line', { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: 'var(--grid)', 'stroke-width': 1 }));
      const tx = sv('text', { x: L - 8, y: y(v) + 4, 'text-anchor': 'end' }); tx.textContent = Math.round(v); svg.append(tx);
    }
    // x축: 월 경계 (범위가 짧으면 주 단위)
    const months = [];
    for (let i = 1; i < pts.length; i++) if (pts[i].d.slice(4, 6) !== pts[i - 1].d.slice(4, 6)) months.push(pts[i]);
    const ticks = months.length >= 2 ? months : pts.filter((_, i) => i % 5 === 0);
    const every = Math.ceil(ticks.length / Math.max(2, Math.floor((W - L - R) / 70)));
    ticks.forEach((p, i) => {
      if (i % every) return;
      const tx = sv('text', { x: x(p.t), y: H - 6, 'text-anchor': 'middle' });
      tx.textContent = months.length >= 2 ? `${+p.d.slice(4, 6)}월` : `${+p.d.slice(4, 6)}/${+p.d.slice(6, 8)}`;
      svg.append(tx);
    });
    svg.append(sv('line', { x1: L, x2: W - R, y1: H - B, y2: H - B, stroke: 'var(--axis)', 'stroke-width': 1 }));

    const path = pts.map((p, i) => (i ? 'L' : 'M') + x(p.t).toFixed(1) + ' ' + y(p.v).toFixed(1)).join('');
    svg.append(sv('path', { d: path, fill: 'none', stroke: 'var(--s1)', 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }));
    for (const o of offs) svg.append(sv('circle', { cx: x(o.t), cy: y(o.official), r: 4.5, fill: 'var(--s2)', stroke: 'var(--surface)', 'stroke-width': 2 }));

    const cross = sv('line', { y1: T, y2: H - B, stroke: 'var(--axis)', 'stroke-width': 1, visibility: 'hidden' });
    const dot = sv('circle', { r: 4, fill: 'var(--s1)', stroke: 'var(--surface)', 'stroke-width': 2, visibility: 'hidden' });
    svg.append(cross, dot);

    function show(i) {
      const p = pts[i], px = x(p.t), py = y(p.v);
      cross.setAttribute('x1', px); cross.setAttribute('x2', px); cross.setAttribute('visibility', 'visible');
      dot.setAttribute('cx', px); dot.setAttribute('cy', py); dot.setAttribute('visibility', 'visible');
      tip.replaceChildren(el('div', { class: 'd' }, fmtDate(p.d)));
      const r1 = el('div', { class: 'row' }); const k1 = el('i'); k1.style.background = 'var(--s1)';
      r1.append(k1, el('b', {}, `${jo(p.v)}조 원`), el('span', {}, '추적값'));
      tip.append(r1);
      const o = offs.find(o => o.date === p.d);
      if (o) {
        const r2 = el('div', { class: 'row' }); const k2 = el('i'); k2.style.background = 'var(--s2)';
        r2.append(k2, el('b', {}, `${jo(o.official)}조 원`), el('span', {}, '공시 월말값'));
        tip.append(r2);
      }
      const i0 = daily.indexOf(p);
      if (i0 > 0) tip.append(el('div', { class: 'muted' }, `전일 대비 ${pct((p.v / daily[i0 - 1].v - 1) * 100)}`));
      tip.style.display = 'block';
      const tw = tip.offsetWidth;
      tip.style.left = Math.max(0, Math.min(px + 12, W - tw)) + 'px';
      tip.style.top = Math.max(0, py - 60) + 'px';
    }
    function hide() { cross.setAttribute('visibility', 'hidden'); dot.setAttribute('visibility', 'hidden'); tip.style.display = 'none'; }
    function nearest(clientX) {
      const r = svg.getBoundingClientRect(), mx = clientX - r.left;
      let best = 0, bd = Infinity;
      pts.forEach((p, i) => { const d = Math.abs(x(p.t) - mx); if (d < bd) { bd = d; best = i; } });
      return best;
    }
    svg.onpointermove = e => show(nearest(e.clientX));
    svg.onpointerleave = hide;
    svg.tabIndex = 0;
    let ki = pts.length - 1;
    svg.onkeydown = e => {
      if (e.key === 'ArrowLeft') ki = Math.max(0, ki - 1); else if (e.key === 'ArrowRight') ki = Math.min(pts.length - 1, ki + 1); else return;
      e.preventDefault(); show(ki);
    };
    svg.onblur = hide;
  }

  document.querySelectorAll('.controls button').forEach(b => b.addEventListener('click', () => {
    document.querySelectorAll('.controls button').forEach(x => x.setAttribute('aria-pressed', 'false'));
    b.setAttribute('aria-pressed', 'true'); range = +b.dataset.range; draw();
  }));
  new ResizeObserver(draw).observe(box);
  draw();

  // 표: 일별 (최근 날짜부터)
  const fillTable = (id, head, rows) => {
    const t = document.getElementById(id);
    const tr = el('tr'); head.forEach(h => tr.append(el('th', {}, h))); t.append(el('thead')); t.tHead.append(tr);
    const tb = el('tbody');
    for (const r of rows) { const row = el('tr'); for (const c of r) { const td = el('td', c.cls ? { class: c.cls } : {}, c.t ?? c); row.append(td); } tb.append(row); }
    t.append(tb);
  };
  fillTable('dailyTable', ['날짜', '평가액(조 원)', '전일 대비'],
    daily.map((p, i) => [fmtDate(p.d), jo(p.v), i ? { t: pct((p.v / daily[i - 1].v - 1) * 100), cls: cls(p.v - daily[i - 1].v) } : '-']).reverse());

  document.getElementById('topSub').textContent = `전체 ${D.n_holdings.toLocaleString('ko-KR')}개 종목 중 최근 평가액 상위 ${D.top.length}개 · 단위: 조 원`;
  fillTable('topTable', ['종목', '2025년 말', '최근', '변화율', '비중'],
    D.top.map(r => [r.name + (r.stale ? ' (거래 종료)' : ''), jo(r.base / 1e4), jo(r.now / 1e4), { t: arrow(r.chg) + pct(r.chg), cls: cls(r.chg) }, r.w.toFixed(1) + '%']));

  fillTable('checkTable', ['월말', '추적값', '공시값', '커버율', '기준 대비', '출처'],
    D.official.map(o => [o.ym.slice(0, 4) + '.' + o.ym.slice(4), jo(o.tracked), jo(o.official), o.cover.toFixed(2) + '%',
      o.ym === D.official[0].ym ? '기준' : (o.gap > 0 ? '+' : '') + o.gap.toFixed(2) + '%p', o.src + (o.trust === '공식' ? '' : ' · 참고용')]));

  document.getElementById('footer').textContent =
    `데이터: 국민연금공단 국내주식 투자정보(2025.12.31), 금융위원회 주식시세정보(공공데이터포털)` +
    (D.stale ? ` · 거래가 끊겨 마지막 종가로 고정된 종목 ${D.stale}개` : '');
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
