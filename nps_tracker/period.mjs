const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function validDate(text) {
  if (!DATE_RE.test(text)) return false;
  const date = new Date(`${text}T00:00:00Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === text;
}

export function periodSummary(rows, startText, endText) {
  if (!startText) return { ok: false, error: '시작일을 입력해 주세요' };
  if (!endText) return { ok: false, error: '종료일을 입력해 주세요' };
  if (!validDate(startText) || !validDate(endText)) {
    return { ok: false, error: '날짜 형식은 YYYY-MM-DD예요' };
  }
  if (startText > endText) return { ok: false, error: '시작일이 종료일보다 늦어요' };

  const ordered = [...rows].sort((a, b) => a.date.localeCompare(b.date));
  if (!ordered.length) return { ok: false, error: '기간 안에 거래일이 없어요' };
  const start = ordered.find(row => row.date >= startText);
  const cappedEndText = endText > ordered.at(-1).date ? ordered.at(-1).date : endText;
  const end = [...ordered].reverse().find(row => row.date <= cappedEndText);
  if (!start || !end || start.date > end.date) {
    return { ok: false, error: '기간 안에 거래일이 없어요' };
  }
  const included = ordered.filter(row => row.date >= start.date && row.date <= end.date);
  const high = included.reduce((best, row) => row.value > best.value ? row : best);
  const low = included.reduce((best, row) => row.value < best.value ? row : best);
  const notice = endText > ordered.at(-1).date ? `최신 거래일 ${ordered.at(-1).date}까지` : null;
  return {
    ok: true, start, end,
    changePct: Number((((end.value - start.value) / start.value) * 100).toFixed(2)),
    tradingDays: included.length, high, low, notice,
  };
}
