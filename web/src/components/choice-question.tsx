"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui";
import { ApiError, api, type AnswerResult, type ChoiceView } from "@/lib/api";

const BLANK = "___";

// Yalnızca olay işleyicisinden çağrılır (render sırasında değil).
function elapsedSince(start: number | null): number | null {
  return start === null ? null : Math.round(performance.now() - start);
}

/** Boşluklu cümlede boşluğu görünür bir çizgiyle gösterir. */
function Prompt({ text }: { text: string }) {
  const [before, after] = text.split(BLANK);
  if (after === undefined) return <p className="text-lg leading-relaxed">{text}</p>;
  return (
    <p className="text-lg leading-relaxed">
      {before}
      <span className="mx-1 inline-block w-16 border-b-2 border-foreground align-baseline" aria-label="boşluk" />
      {after}
    </p>
  );
}

/**
 * Tek doğru cevaplı seçmeli soru. Cevap sunucuda değerlendirilir; istemci yalnızca
 * seçimi gönderir. İpucu kullanılırsa derece "Hard" olur (sunucu kuralı).
 */
export function ChoiceQuestion({
  activityId,
  question,
  hintTr,
  onAnswered,
}: {
  activityId: number;
  question: ChoiceView;
  hintTr?: string | null;
  onAnswered: (correct: boolean) => void;
}) {
  const [hinted, setHinted] = useState(false);
  const [chosen, setChosen] = useState<string | null>(null);
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Soru ekrana geldiği an; cevap süresi (duration_ms) buradan ölçülür.
  const shownAt = useRef<number | null>(null);
  useEffect(() => {
    shownAt.current = performance.now();
  }, []);

  async function choose(option: string) {
    if (chosen) return;
    setChosen(option);
    try {
      const res = await api.answer(activityId, {
        question_id: question.id,
        answer: option,
        hinted,
        duration_ms: elapsedSince(shownAt.current),
      });
      setResult(res);
    } catch (err) {
      setChosen(null);
      setError(err instanceof ApiError ? err.message : "Gönderilemedi, tekrar dene.");
    }
  }

  function optionClass(option: string): string {
    if (!result) return "border-line bg-card hover:bg-muted";
    if (option === result.correct_answer) return "border-accent bg-card text-accent font-medium";
    if (option === chosen) return "border-danger bg-card text-danger line-through";
    return "border-line bg-card opacity-60";
  }

  return (
    <div className="flex flex-col gap-3">
      <Prompt text={question.prompt} />
      {hintTr &&
        (hinted ? (
          <p className="text-sm text-subtle">İpucu: {hintTr}</p>
        ) : (
          !result && (
            <button
              type="button"
              onClick={() => setHinted(true)}
              className="self-start text-sm text-accent underline-offset-4 hover:underline"
            >
              İpucu göster
            </button>
          )
        ))}
      <div className="flex flex-col gap-2">
        {question.options.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => choose(option)}
            disabled={chosen !== null}
            className={`min-h-12 rounded-xl border px-4 text-left text-base transition ${optionClass(option)}`}
          >
            {option}
          </button>
        ))}
      </div>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      {result && (
        <>
          <p className={result.correct ? "text-accent" : "text-danger"} role="status">
            {result.correct ? "Doğru!" : `Doğrusu: ${result.correct_answer}`}
          </p>
          <Button onClick={() => onAnswered(result.correct)}>Devam</Button>
        </>
      )}
    </div>
  );
}
