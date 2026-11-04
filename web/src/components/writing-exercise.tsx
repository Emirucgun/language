"use client";

import { type FormEvent, useState } from "react";

import { FeedbackPanel } from "@/components/feedback-panel";
import { Button, Card, ErrorText, inputClass } from "@/components/ui";
import { ApiError, api, type FeedbackView } from "@/lib/api";

// Akış (blueprint, Bölüm 3): yaz → önce ipucu + Türkçe açıklama → yeniden yaz → doğrusu.
type Stage =
  | { kind: "compose" }
  | { kind: "waiting" }
  | { kind: "feedback"; text: string; view: FeedbackView }
  | { kind: "deferred" };

export function WritingExercise({
  taskTr,
  send,
  activityId,
  onFinished,
  finishLabel,
}: {
  taskTr: string;
  send: (text: string) => Promise<FeedbackView>;
  activityId?: number;
  onFinished: () => void;
  finishLabel: string;
}) {
  const [stage, setStage] = useState<Stage>({ kind: "compose" });
  const [text, setText] = useState("");
  const [complete, setComplete] = useState(false);
  const [flagged, setFlagged] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setStage({ kind: "waiting" });
    setError(null);
    try {
      const view = await send(text.trim());
      setStage(view.status === "shown" ? { kind: "feedback", text: text.trim(), view } : { kind: "deferred" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gönderilemedi, tekrar dene.");
      setStage({ kind: "compose" });
    }
  }

  function flag() {
    setFlagged(true);
    void api.event({ type: "activity_flagged", payload: {}, activity_id: activityId ?? null });
  }

  const finished = stage.kind === "deferred" || (stage.kind === "feedback" && complete);

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <p className="text-lg">{taskTr}</p>
      </Card>

      {(stage.kind === "compose" || stage.kind === "waiting") && (
        <form onSubmit={submit} className="flex flex-col gap-3">
          <label htmlFor="answer" className="sr-only">
            Cümlen
          </label>
          <textarea
            id="answer"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={3}
            maxLength={1000}
            lang="en"
            spellCheck={false}
            autoCapitalize="sentences"
            placeholder="İngilizce cümleni buraya yaz"
            className={`${inputClass} py-3`}
            disabled={stage.kind === "waiting"}
          />
          <Button type="submit" disabled={!text.trim() || stage.kind === "waiting"}>
            {stage.kind === "waiting" ? "Geri bildirim hazırlanıyor…" : "Gönder"}
          </Button>
        </form>
      )}

      {stage.kind === "deferred" && (
        <Card>
          <p>
            Şimdilik atladık. Cümleni kaydettik; geri bildirimin hazır olunca panelde
            göreceksin.
          </p>
        </Card>
      )}

      {stage.kind === "feedback" && (
        <FeedbackPanel
          text={stage.text}
          view={stage.view}
          activityId={activityId}
          onComplete={() => setComplete(true)}
        />
      )}

      <ErrorText message={error} />

      {finished && <Button onClick={onFinished}>{finishLabel}</Button>}

      {stage.kind !== "compose" && stage.kind !== "waiting" && (
        <button
          type="button"
          onClick={flag}
          disabled={flagged}
          className="self-start text-sm text-subtle underline-offset-4 hover:underline disabled:no-underline"
        >
          {flagged ? "Bildirildi, teşekkürler." : "Bu etkinlikte sorun var"}
        </button>
      )}
    </div>
  );
}
