"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Button, Card, ErrorText, Loading, Screen, inputClass } from "@/components/ui";
import { ApiError, api, type ReviewQueueView, type Schemas } from "@/lib/api";
import { nextPath, useMe } from "@/lib/use-me";

type Verdict = Schemas["ReviewRequest"]["verdict"];

// Tanımlar docs/content/inceleme-yonergesi.md ile aynı kalmalı.
const VERDICTS: { value: Verdict; label: string; hint: string; primary?: boolean }[] = [
  { value: "correct", label: "Doğru", hint: "Öğrenciye olduğu gibi gösterilebilir.", primary: true },
  {
    value: "wrong_teaching",
    label: "Yanlış öğretiyor",
    hint: "Öğrenci bunu öğrenirse yanlış öğrenir. İçerik başka öğrencilere gitmez.",
  },
  { value: "off_level", label: "Seviye dışı", hint: "Doğru ama A1–A2 için fazla zor." },
  { value: "unclear", label: "Anlaşılmıyor", hint: "Doğru ama soru ya da açıklama kafa karıştırıyor." },
];

// Işıl'ın inceleme ekranı: önce "sorun var" işaretlileri, sonra rastgele örnek.
export default function ReviewPage() {
  const me = useMe("review");
  const [queue, setQueue] = useState<ReviewQueueView | null>(null);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .reviewNext()
      .then(setQueue)
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Kuyruk yüklenemedi."));
  }, []);

  useEffect(() => {
    if (me) load();
  }, [me, load]);

  if (!me) return <Screen><Loading /></Screen>;

  async function decide(verdict: Verdict) {
    const item = queue?.item;
    if (!item || saving) return;
    setSaving(true);
    setError(null);
    try {
      await api.review({
        target_type: item.target_type,
        target_id: item.target_id,
        verdict,
        notes: notes.trim() || null,
      });
      setNotes("");
      setQueue(null);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Kaydedilemedi, tekrar dene.");
    } finally {
      setSaving(false);
    }
  }

  const item = queue?.item;

  return (
    <Screen title="İnceleme">
      <div className="-mt-4 flex flex-col gap-2 text-sm text-subtle">
        <Link href={nextPath(me)} className="self-end underline-offset-4 hover:underline">
          Öğrenci ekranı →
        </Link>
        <details>
          <summary className="cursor-pointer">Kararlar ne anlama geliyor?</summary>
          <dl className="mt-2 flex flex-col gap-2">
            {VERDICTS.map((verdict) => (
              <div key={verdict.value}>
                <dt className="font-medium text-foreground">{verdict.label}</dt>
                <dd>{verdict.hint}</dd>
              </div>
            ))}
          </dl>
        </details>
      </div>

      {queue && (
        <p className="text-sm text-subtle">
          Örnek: {queue.stats.sample_reviewed} incelendi, {queue.stats.sample_wrong_teaching} yanlış öğretiyor ·{" "}
          {queue.stats.flags_pending} sorun bildirimi bekliyor
        </p>
      )}

      {!queue && !error && <Loading />}

      {queue && !item && (
        <Card>
          <p>İncelenecek bir şey kalmadı. Teşekkürler.</p>
        </Card>
      )}

      {item && (
        <>
          <Card className="flex flex-col gap-3">
            <div className="flex items-center justify-between gap-2 text-sm">
              <span className="font-medium">{item.title}</span>
              <span className="rounded-full bg-muted px-2 py-0.5 text-subtle">
                {item.source === "flag" ? "Sorun bildirildi" : "Rastgele örnek"}
                {item.level ? ` · ${item.level}` : ""}
              </span>
            </div>
            {item.flag_reason && <p className="text-sm text-danger">Öğrencinin notu: {item.flag_reason}</p>}
            <dl className="flex flex-col gap-3">
              {item.lines.map((line, index) => (
                <div key={index}>
                  <dt className="text-sm text-subtle">{line.label}</dt>
                  <dd className="text-lg leading-relaxed">{line.text}</dd>
                </div>
              ))}
            </dl>
          </Card>

          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            maxLength={2000}
            rows={2}
            placeholder="Not (isteğe bağlı)"
            aria-label="Not"
            className={`${inputClass} py-2`}
          />

          <div className="grid grid-cols-2 gap-2">
            {VERDICTS.map((verdict) => (
              <Button
                key={verdict.value}
                variant={verdict.primary ? "primary" : "secondary"}
                disabled={saving}
                onClick={() => decide(verdict.value)}
              >
                {verdict.label}
              </Button>
            ))}
          </div>
        </>
      )}

      <ErrorText message={error} />
    </Screen>
  );
}
