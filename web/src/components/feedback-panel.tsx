"use client";

import { type FormEvent, useEffect, useId, useState } from "react";

import { MarkedText } from "@/components/marked-text";
import { Button, Card, ErrorText, inputClass } from "@/components/ui";
import { ApiError, api, type FeedbackView } from "@/lib/api";

/**
 * Gösterilmiş bir geri bildirim: işaretli cümle, ipucu, katalog açıklaması, "anladım"
 * tepkisi, yeniden yazma ve ancak ondan sonra doğru cümle. Hem anında hem gecikmeli
 * geri bildirimde aynı akış. Görüldüğünde `feedback_shown` olayı yazılır.
 */
export function FeedbackPanel({
  text,
  view,
  activityId,
  onComplete,
}: {
  text: string;
  view: FeedbackView;
  activityId?: number;
  onComplete?: () => void;
}) {
  const [rewrite, setRewrite] = useState("");
  const [correction, setCorrection] = useState<string | null | undefined>(undefined);
  const [reacted, setReacted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const rewriteId = useId();

  useEffect(() => {
    void api.event({
      type: "feedback_shown",
      payload: { feedback_id: view.feedback_id ?? null },
      activity_id: activityId ?? null,
    });
    if (view.is_correct) onComplete?.();
    // Yalnızca ilk gösterimde.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view.feedback_id]);

  async function submitRewrite(e: FormEvent) {
    e.preventDefault();
    if (view.feedback_id == null) return;
    try {
      const result = await api.rewrite(view.feedback_id, rewrite.trim(), activityId);
      setCorrection(result.correction);
      onComplete?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gönderilemedi, tekrar dene.");
    }
  }

  function react(understood: boolean) {
    if (view.feedback_id == null) return;
    setReacted(true);
    void api.event({
      type: "feedback_reaction",
      payload: { feedback_id: view.feedback_id, understood },
      activity_id: activityId ?? null,
    });
  }

  if (view.is_correct) {
    return (
      <Card className="border-accent">
        <p className="text-lg font-medium text-accent">Doğru!</p>
        <p className="mt-2 text-lg">{text}</p>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card className="flex flex-col gap-3">
        <MarkedText text={text} errors={view.errors ?? []} />
        {view.hint_tr && (
          <p>
            <span className="font-medium">İpucu: </span>
            {view.hint_tr}
          </p>
        )}
      </Card>

      {(view.errors ?? []).map((err, i) => (
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
          <label htmlFor={rewriteId} className="text-sm font-medium">
            Şimdi kendin düzeltip yeniden yaz
          </label>
          <textarea
            id={rewriteId}
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
      <ErrorText message={error} />
    </div>
  );
}
