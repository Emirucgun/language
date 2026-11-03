import type { ShownError } from "@/lib/api";

/**
 * Öğrencinin cümlesini hataların yerleri işaretli gösterir. Boş aralık (eksik kelime)
 * araya bir işaret (‸) koyar. Çakışan aralıklarda ilki kazanır.
 */
export function MarkedText({ text, errors }: { text: string; errors: readonly ShownError[] }) {
  const sorted = [...errors].sort((a, b) => a.start - b.start || a.end - b.end);
  const parts: React.ReactNode[] = [];
  let cursor = 0;

  sorted.forEach((error, i) => {
    if (error.start < cursor) return;
    parts.push(text.slice(cursor, error.start));
    if (error.end === error.start) {
      parts.push(
        <mark key={i} className="rounded bg-mark px-0.5 text-foreground font-bold" title={error.name_tr}>
          ‸
        </mark>,
      );
    } else {
      parts.push(
        <mark key={i} className="rounded bg-mark px-0.5 text-foreground" title={error.name_tr}>
          {text.slice(error.start, error.end)}
        </mark>,
      );
    }
    cursor = Math.max(cursor, error.end);
  });
  parts.push(text.slice(cursor));

  return <p className="text-lg leading-relaxed">{parts}</p>;
}
