"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useId, useRef, useState } from "react";

import { MarkedText } from "@/components/marked-text";
import { Button, Card, ErrorText, Loading, Screen, inputClass } from "@/components/ui";
import { ApiError, api, type DialogueView, type FeedbackView, type PartnerLine } from "@/lib/api";
import { useMe } from "@/lib/use-me";

/**
 * Yazılı diyalog (4–6 tur): senaryo ve açılış sabit, her cümleye kısa geri bildirim ve
 * partnerin cevabı tek istekle gelir. Geri bildirimde önce ipucu, istenirse açıklama.
 */
export default function DialoguePage() {
  const me = useMe("app");
  const [dialogue, setDialogue] = useState<DialogueView | null>(null);
  const [round, setRound] = useState(0);
  const [text, setText] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [fresh, setFresh] = useState(-1); // yeni gelen turun sırası: yalnızca o "gösterildi" sayılır
  const [error, setError] = useState<string | null>(null);
  const requested = useRef(-1);
  const inputId = useId();
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!me || requested.current === round) return;
    requested.current = round;
    api
      .dialogueStart()
      .then(setDialogue)
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Başlatılamadı."));
  }, [me, round]);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [dialogue?.turns.length, pending]);

  if (!me) return <Screen><Loading /></Screen>;

  async function send(e: FormEvent) {
    e.preventDefault();
    if (!dialogue || !text.trim() || pending) return;
    const line = text.trim();
    setPending(line);
    setText("");
    setError(null);
    try {
      const next = await api.dialogueReply(dialogue.activity_id, line);
      setFresh(next.turns.length - 1);
      setDialogue(next);
    } catch (err) {
      setText(line);
      setError(err instanceof ApiError ? err.message : "Gönderilemedi, tekrar dene.");
    } finally {
      setPending(null);
    }
  }

  function restart() {
    setDialogue(null);
    setFresh(-1);
    setError(null);
    setRound((r) => r + 1);
  }

  return (
    <Screen title="Yazılı diyalog">
      <Link href="/panel" className="-mt-4 text-sm text-subtle underline-offset-4 hover:underline">
        ← Panele dön
      </Link>
      {!dialogue && !error && <Loading label="Senaryo hazırlanıyor…" />}

      {dialogue && (
        <>
          <Card className="flex flex-col gap-2 bg-muted">
            <p className="font-medium">{dialogue.scenario_tr}</p>
            <p className="text-sm">
              Sen: <span className="font-medium">{dialogue.learner_role_tr}</span> · Karşındaki:{" "}
              <span className="font-medium">{dialogue.partner_role_tr}</span>
            </p>
            {dialogue.target_items.length > 0 && (
              <p className="text-sm">
                Kullanmaya çalış:{" "}
                <span lang="en" className="font-medium">
                  {dialogue.target_items.join(", ")}
                </span>
              </p>
            )}
          </Card>

          <div className="flex flex-col gap-3" aria-live="polite">
            <PartnerBubble line={dialogue.opening} />
            {dialogue.turns.map((turn, i) => (
              <div key={i} className="flex flex-col gap-3">
                <LearnerBubble text={turn.learner} />
                {turn.feedback && (
                  <TurnFeedback
                    text={turn.learner}
                    view={turn.feedback}
                    activityId={dialogue.activity_id}
                    fresh={i === fresh}
                  />
                )}
                <PartnerBubble line={turn.partner} />
              </div>
            ))}
            {pending && (
              <>
                <LearnerBubble text={pending} />
                <p className="text-sm text-subtle">Yazıyor…</p>
              </>
            )}
            <div ref={end} />
          </div>

          {dialogue.done ? (
            <Card className="flex flex-col gap-3 border-accent">
              <p className="text-lg font-medium">Diyalog tamamlandı.</p>
              <p className="text-sm text-subtle">{dialogue.turns.length} cümle yazdın.</p>
              <Button onClick={restart}>Yeni diyalog</Button>
            </Card>
          ) : (
            <form onSubmit={send} className="flex flex-col gap-3">
              <label htmlFor={inputId} className="text-sm font-medium">
                Cevabın{" "}
                <span className="font-normal text-subtle">
                  ({Math.min(dialogue.turns.length + 1, dialogue.max_turns)}. cümle,{" "}
                  {dialogue.min_turns}–{dialogue.max_turns} arası)
                </span>
              </label>
              <textarea
                id={inputId}
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    e.currentTarget.form?.requestSubmit();
                  }
                }}
                rows={2}
                maxLength={300}
                lang="en"
                spellCheck={false}
                disabled={pending !== null}
                className={`${inputClass} py-3`}
              />
              <Button type="submit" disabled={!text.trim() || pending !== null}>
                Gönder
              </Button>
            </form>
          )}
        </>
      )}
      <ErrorText message={error} />
    </Screen>
  );
}

function PartnerBubble({ line }: { line: PartnerLine }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mr-8 flex flex-col items-start gap-1">
      <p lang="en" className="rounded-2xl rounded-tl-sm border border-line bg-card px-4 py-3 text-lg">
        {line.en}
      </p>
      {open ? (
        <p className="px-1 text-sm text-subtle">{line.tr}</p>
      ) : (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="px-1 text-sm text-subtle underline-offset-4 hover:underline"
        >
          Türkçesi
        </button>
      )}
    </div>
  );
}

function LearnerBubble({ text }: { text: string }) {
  return (
    <p lang="en" className="ml-8 self-end rounded-2xl rounded-tr-sm bg-foreground px-4 py-3 text-lg text-background">
      {text}
    </p>
  );
}

/** Konuşmayı bölmeyen kısa geri bildirim: işaret + ipucu; açıklama istenirse. */
function TurnFeedback({
  text,
  view,
  activityId,
  fresh,
}: {
  text: string;
  view: FeedbackView;
  activityId: number;
  fresh: boolean;
}) {
  const [explained, setExplained] = useState(false);
  const [reacted, setReacted] = useState(false);

  useEffect(() => {
    if (!fresh) return;
    void api.event({
      type: "feedback_shown",
      payload: { feedback_id: view.feedback_id ?? null },
      activity_id: activityId,
    });
  }, [fresh, view.feedback_id, activityId]);

  if (view.is_correct) {
    return <p className="ml-8 self-end text-sm text-accent">Doğru ✓</p>;
  }

  function react(understood: boolean) {
    if (view.feedback_id == null) return;
    setReacted(true);
    void api.event({
      type: "feedback_reaction",
      payload: { feedback_id: view.feedback_id, understood },
      activity_id: activityId,
    });
  }

  return (
    <Card className="ml-8 flex flex-col gap-2 text-sm">
      <MarkedText text={text} errors={view.errors ?? []} />
      {view.hint_tr && (
        <p>
          <span className="font-medium">İpucu: </span>
          {view.hint_tr}
        </p>
      )}
      {!explained ? (
        <button
          type="button"
          onClick={() => setExplained(true)}
          className="self-start text-subtle underline-offset-4 hover:underline"
        >
          Açıklamayı göster
        </button>
      ) : (
        <>
          {(view.errors ?? []).map((err, i) => (
            <div key={i} className="rounded-xl bg-muted p-3">
              <p className="font-medium">{err.name_tr}</p>
              <p className="leading-relaxed">{err.explanation_tr}</p>
            </div>
          ))}
          {!reacted ? (
            <div className="flex gap-2">
              <Button variant="secondary" className="min-h-10 flex-1 text-sm" onClick={() => react(true)}>
                Anladım
              </Button>
              <Button variant="secondary" className="min-h-10 flex-1 text-sm" onClick={() => react(false)}>
                Anlamadım
              </Button>
            </div>
          ) : (
            <p className="text-subtle">Teşekkürler.</p>
          )}
        </>
      )}
    </Card>
  );
}
