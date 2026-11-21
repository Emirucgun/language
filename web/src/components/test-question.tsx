"use client";

const BLANK = "___";

/** Ölçüm testlerinin ortak parçaları: doğru cevap gösterilmez, "Bilmiyorum" hep vardır. */
export function BlankPrompt({ text, lang }: { text: string; lang?: string }) {
  const [before, after] = text.split(BLANK);
  if (after === undefined) return <p className="text-lg leading-relaxed">{text}</p>;
  return (
    <p className="text-lg leading-relaxed" lang={lang}>
      {before}
      <span className="mx-1 inline-block w-16 border-b-2 border-foreground align-baseline" aria-label="boşluk" />
      {after}
    </p>
  );
}

export function TestProgress({ done, total }: { done: number; total: number }) {
  return (
    <>
      <div className="flex items-center justify-between text-sm text-subtle">
        <span>
          {Math.min(done + 1, total)} / {total}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted" aria-hidden>
        <div className="h-full bg-accent transition-all" style={{ width: `${(done / total) * 100}%` }} />
      </div>
    </>
  );
}

export function TestOptions({
  options,
  busy,
  onChoose,
}: {
  options: string[];
  busy: boolean;
  onChoose: (answer: string) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      {options.map((option) => (
        <button
          key={option}
          type="button"
          disabled={busy}
          onClick={() => onChoose(option)}
          lang="en"
          className="min-h-12 rounded-xl border border-line bg-card px-4 text-left text-base transition hover:bg-muted disabled:opacity-60"
        >
          {option}
        </button>
      ))}
      <button
        type="button"
        disabled={busy}
        onClick={() => onChoose("")}
        className="min-h-12 rounded-xl border border-dashed border-line px-4 text-left text-subtle transition hover:bg-muted disabled:opacity-60"
      >
        Bilmiyorum
      </button>
    </div>
  );
}
