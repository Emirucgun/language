"use client";

import { type FormEvent, useState } from "react";

import { MarkedText } from "@/components/marked-text";
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
  const [rewrite, setRewrite] = useState("");
  const [correction, setCorrection] = useState<string | null | undefined>(undefined);
  const [reacted, setReacted] = useState(false);
  const [flagged, setFlagged] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setStage({ kind: "waiting" });
    setError(null);
    try {
      const view = await send(text.trim());
      if (view.status === "shown") {
        setStage({ kind: "feedback", text: text.trim(), view });
        void api.event({ type: "feedback_shown", payload: {}, activity_id: activityId ?? null });
      } else {
        setStage({ kind: "deferred" });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gönderilemedi, tekrar dene.");
      setStage({ kind: "compose" });
    }
  }

  async function submitRewrite(e: FormEvent) {
    e.preventDefault();
    if (stage.kind !== "feedback" || stage.view.feedback_id == null) return;
    try {
      const result = await api.rewrite(stage.view.feedback_id, rewrite.trim(), activityId);
      setCorrection(result.correction);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gönderilemedi, tekrar dene.");
    }
  }

  function react(understood: boolean) {
    if (stage.kind !== "feedback" || stage.view.feedback_id == null) return;
    setReacted(true);
    void api.event({
      type: "feedback_reaction",
      payload: { feedback_id: stage.view.feedback_id, understood },
      activity_id: activityId ?? null,
    });
  }

  function flag() {
    setFlagged(true);
    void api.event({ type: "activity_flagged", payload: {}, activity_id: activityId ?? null });
  }

  const finished =
    stage.kind === "deferred" ||
    (stage.kind === "feedback" && (stage.view.is_correct || correction !== undefined));

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
          <p>Şimdilik atladık. Cümleni kaydettik; geri bildirimini sonra göreceksin.</p>
        </Card>
      )}

      {stage.kind === "feedback" && stage.view.is_correct && (
        <Card className="border-accent">
          <p className="text-lg font-medium text-accent">Doğru!</p>
          <p className="mt-2 text-lg">{stage.text}</p>
        </Card>
      )}

      {stage.kind === "feedback" && !stage.view.is_correct && (
        <div className="flex flex-col gap-4">
          <Card className="flex flex-col gap-3">
            <MarkedText text={stage.text} errors={stage.view.errors ?? []} />
            {stage.view.hint_tr && (
              <p>
                <span className="font-medium">İpucu: </span>
                {stage.view.hint_tr}
              </p>
            )}
          </Card>

          {(stage.view.errors ?? []).map((err, i) => (
            <Card key={i} className="flex flex-col gap-1 bg-muted">
              <p className="font-medium">{err.name_tr}</p>
              <p className="text-sm leading-relaxed">{err.explanation_tr}</p>
            </Card>
          ))}

          {!reacted ? (
            <div className="flex flex-col gap-2">
              <p className="text-sm text-subtle">Açıklama işine yaradı mı?</p>
              <div className="grid grid-cols-2 gap-2">
                <Button variant="secondary" onClick={() => react(true)}>
                  Anladım
                </Button>
                <Button variant="secondary" onClick={() => react(false)}>
                  Anlamadım
                </Button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-subtle">Teşekkürler.</p>
          )}

          {correction === undefined ? (
            <form onSubmit={submitRewrite} className="flex flex-col gap-3">
              <label htmlFor="rewrite" className="text-sm font-medium">
                Şimdi kendin düzeltip yeniden yaz
              </label>
              <textarea
                id="rewrite"
                value={rewrite}
                onChange={(e) => setRewrite(e.target.value)}
                rows={3}
                maxLength={1000}
                lang="en"
                spellCheck={false}
                className={`${inputClass} py-3`}
              />
              <Button type="submit" disabled={!rewrite.trim()}>
                Yeniden gönder
              </Button>
            </form>
          ) : (
            <Card className="border-accent">
              <p className="text-sm text-subtle">Senin cevabın: {rewrite.trim()}</p>
              <p className="mt-2 text-lg">
                <span className="font-medium">Doğrusu: </span>
                {correction ?? "—"}
              </p>
            </Card>
          )}
        </div>
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
