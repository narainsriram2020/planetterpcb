const TERMS: Record<string, string> = { "01": "Spring", "05": "Summer", "08": "Fall", "12": "Winter" };

/** PlanetTerp semester code "202508" -> "Fall 2025". */
export function formatSemester(code: string | null | undefined): string {
  if (!code || code.length !== 6) return code ?? "";
  return `${TERMS[code.slice(4)] ?? code.slice(4)} ${code.slice(0, 4)}`;
}

/** "202308-202508 (YYYYMM; ...)" -> "Fall 2023 – Fall 2025". */
export function formatSemesterRange(range: string | null | undefined): string {
  const match = range?.match(/(\d{6})-(\d{6})/);
  if (!match) return "";
  return `${formatSemester(match[1])} – ${formatSemester(match[2])}`;
}

export function formatGpa(gpa: number | null | undefined): string {
  return typeof gpa === "number" ? gpa.toFixed(2) : "—";
}

export function formatCount(n: number | null | undefined): string {
  return typeof n === "number" ? n.toLocaleString("en-US") : "—";
}

/** "MATH141" -> "MATH 141" for display. */
export function spacedCourse(id: string): string {
  return id.replace(/^([A-Z]{4})(\d)/, "$1 $2");
}
