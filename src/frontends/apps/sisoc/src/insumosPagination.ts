export function pageRange(current: number, total: number): Array<number | "…"> {
  if (total <= 0) return [];
  const start = Math.max(1, current - 4);
  const end = Math.min(total, current + 4);
  const range: Array<number | "…"> = [];
  if (start > 1) {
    range.push(1);
    if (start > 2) range.push("…");
  }
  for (let page = start; page <= end; page += 1) range.push(page);
  if (end < total) {
    if (end < total - 1) range.push("…");
    range.push(total);
  }
  return range;
}
