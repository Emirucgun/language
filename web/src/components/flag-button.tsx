"use client";

import { useState } from "react";

import { api } from "@/lib/api";

const REASONS = ["Yanlış bilgi", "Anlamadım", "Başka bir sorun"];

/**
 * "Sorun var": içerik Işıl'ın inceleme kuyruğuna düşer. Neden sabit bir listeden seçilir;
 * serbest metin kişisel bilgi ve gürültü demek.
 */
export function FlagButton({
  activityId,
  feedbackId,
  label = "Bu etkinlikte sorun var",
}: {
  activityId?: number | null;
  feedbackId?: number | null;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const [sent, setSent] = useState(false);
  const [failed, setFailed] = useState(false);

  if (activityId == null && feedbackId == null) return null;
  if (sent) return <p className="text-sm text-subtle">Bildirildi, teşekkürler.</p>;

  async function send(reason: string) {
    setFailed(false);
    try {
      await api.event({
        type: "activity_flagged",
        payload: feedbackId == null ? { reason } : { reason, feedback_id: feedbackId },
        activity_id: activityId ?? null,
      });
      setSent(true);
    } catch {
      setFailed(true);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="self-start text-sm text-subtle underline-offset-4 hover:underline"
      >
        {label}
      </button>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm text-subtle">Sorun ne?</p>
      <div className="flex flex-wrap gap-2">
        {REASONS.map((reason) => (
          <button
            key={reason}
            type="button"
            onClick={() => send(reason)}
            className="min-h-10 rounded-xl border border-line bg-card px-3 text-sm hover:bg-muted"
          >
            {reason}
          </button>
        ))}
      </div>
      {failed && (
        <p role="alert" className="text-sm text-danger">
          Gönderilemedi, tekrar dene.
        </p>
      )}
    </div>
  );
}
