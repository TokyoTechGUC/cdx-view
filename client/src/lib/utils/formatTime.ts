export function formatTime(t: string): string {
  if (!t) return "";
  // UTC: ends with Z
  if (t.endsWith("Z")) {
    const d = new Date(t);
    if (!Number.isNaN(d.getTime()))
      return d.toISOString().replace("T", " ").slice(0, 16) + " UTC";
  }
  // Offset-aware: +HH:MM or -HH:MM suffix
  const withOffset = t.match(
    /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}).*?([+-]\d{2}:\d{2})$/,
  );
  if (withOffset) return withOffset[1].replace("T", " ") + " " + withOffset[2];
  // Naive ISO datetime: display as-is, no timezone label
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(t))
    return t.replace("T", " ").slice(0, 16);
  // Anything else: return as-is
  return t;
}
