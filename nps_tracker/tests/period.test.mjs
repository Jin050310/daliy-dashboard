// T05 고정 검사 10개 — 기간 변동 조회
// 실행: nps_tracker 폴더에서  node --test tests/period.test.mjs
//
// 이 파일은 AI A 시작 전에 고정했다. 검사 삭제·조건 완화·기대값 변경 금지 (T05-C18~C20).
// 데이터: tests/fixtures/period_sample.csv
//   = 실제 data/daily_value.csv 의 2026-10-26 ~ 2026-11-03 7거래일을 그대로 복사한 것.
//
// 구현해야 할 것: nps_tracker/period.mjs 의
//   export function periodSummary(rows, startText, endText)
//     rows: [{ date: 'YYYY-MM-DD', value: 숫자(조 원) }, ...] 날짜 오름차순
//     startText, endText: 사용자가 입력한 문자열 그대로
//   성공: { ok: true, start: {date, value}, end: {date, value}, changePct, tradingDays,
//           high: {date, value}, low: {date, value}, notice }
//         changePct = (end - start) / start * 100 을 소수 둘째 자리로 반올림한 숫자
//         notice = 안내 문구 문자열 또는 null
//   실패: { ok: false, error: '오류 문구' }
// 규칙: 시작일이 휴장일이면 그 뒤 첫 거래일, 종료일이 휴장일이면 그 앞 마지막 거래일을 쓴다.
//       종료일이 데이터 마지막 날보다 뒤면 마지막 거래일까지로 자르고 안내한다.

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const csv = readFileSync(new URL('./fixtures/period_sample.csv', import.meta.url), 'utf8').replace(/^﻿/, '');
const ROWS = csv.trim().split(/\r?\n/).slice(1).map(line => {
  const [d, v] = line.split(',');
  return { date: `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`, value: Number(v) };
});

let periodSummary = null;
try {
  ({ periodSummary } = await import('../period.mjs'));
} catch {
  // 아직 구현 전이면 각 검사가 개별 FAIL 로 집계된다.
}
function run(start, end) {
  if (typeof periodSummary !== 'function') throw new Error('period.mjs 의 periodSummary 가 아직 없습니다');
  return periodSummary(ROWS, start, end);
}

test('T05-T01 정상: 2026-10-26 ~ 2026-11-03', () => {
  const r = run('2026-10-26', '2026-11-03');
  assert.equal(r.ok, true);
  assert.deepEqual(r.start, { date: '2026-10-26', value: 344.257 });
  assert.deepEqual(r.end, { date: '2026-11-03', value: 355.5443 });
  assert.equal(r.changePct, 3.28);
  assert.equal(r.tradingDays, 7);
});

test('T05-T02 정상(하락): 2026-11-02 ~ 2026-11-03', () => {
  const r = run('2026-11-02', '2026-11-03');
  assert.equal(r.ok, true);
  assert.deepEqual(r.start, { date: '2026-11-02', value: 369.2589 });
  assert.deepEqual(r.end, { date: '2026-11-03', value: 355.5443 });
  assert.equal(r.changePct, -3.71);
});

test('T05-T03 최고·최저일: 2026-10-26 ~ 2026-11-03', () => {
  const r = run('2026-10-26', '2026-11-03');
  assert.equal(r.ok, true);
  assert.deepEqual(r.high, { date: '2026-10-28', value: 379.6022 });
  assert.deepEqual(r.low, { date: '2026-10-26', value: 344.257 });
});

test('T05-T04 경계(같은 날): 2026-11-02 ~ 2026-11-02', () => {
  const r = run('2026-11-02', '2026-11-02');
  assert.equal(r.ok, true);
  assert.equal(r.changePct, 0);
  assert.equal(r.tradingDays, 1);
});

test('T05-T05 경계(양 끝 휴장일): 2026-10-25(일) ~ 2026-11-01(일)', () => {
  const r = run('2026-10-25', '2026-11-01');
  assert.equal(r.ok, true);
  assert.deepEqual(r.start, { date: '2026-10-26', value: 344.257 });
  assert.deepEqual(r.end, { date: '2026-10-30', value: 361.0884 });
  assert.equal(r.changePct, 4.89);
  assert.equal(r.tradingDays, 5);
});

test('T05-T06 경계(데이터 범위 초과): 2026-10-26 ~ 2026-12-31', () => {
  const r = run('2026-10-26', '2026-12-31');
  assert.equal(r.ok, true);
  assert.deepEqual(r.end, { date: '2026-11-03', value: 355.5443 });
  assert.equal(r.notice, '최신 거래일 2026-11-03까지');
});

test('T05-T07 오류(순서): 2026-11-03 ~ 2026-10-26', () => {
  assert.deepEqual(run('2026-11-03', '2026-10-26'), { ok: false, error: '시작일이 종료일보다 늦어요' });
});

test('T05-T08 오류(거래일 없음): 2026-10-31 ~ 2026-11-01', () => {
  assert.deepEqual(run('2026-10-31', '2026-11-01'), { ok: false, error: '기간 안에 거래일이 없어요' });
});

test('T05-T09 오류(형식): 2026/10/26 ~ 2026-11-03', () => {
  assert.deepEqual(run('2026/10/26', '2026-11-03'), { ok: false, error: '날짜 형식은 YYYY-MM-DD예요' });
});

test('T05-T10 오류(빈 입력): (빈칸) ~ 2026-11-03', () => {
  assert.deepEqual(run('', '2026-11-03'), { ok: false, error: '시작일을 입력해 주세요' });
});
