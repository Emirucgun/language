"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { BlankPrompt, TestOptions, TestProgress } from "@/components/test-question";
import { Button, Card, ErrorText, Loading, Screen } from "@/components/ui";
import { ApiError, api, type Schemas } from "@/lib/api";
import { useMe } from "@/lib/use-me";

type View = Schemas["PlacementView"];
type Result = Schemas["PlacementResult"];

const LEVEL_TEXT: Record<string, string> = {
  "pre-A1": "Başlangıç (A1 öncesi)",
  A1: "A1",
  A2: "A2",
};

// Yalnızca olay işleyicisinden çağrılır (render sırasında değil).
function elapsedSince(start: number | null): number | null {
  return start === null ? null : Math.round(performance.now() - start);
}

/**
 * Yerleştirme testi (sabit sorular). Test sırasında doğru cevap gösterilmez: amaç ölçmek.
 * Yarıda bırakılırsa kaldığı sorudan devam eder (cevaplar sunucuda olay olarak durur).
 */
export default function PlacementPage() {
  const me = useMe("placement");
  const router = useRouter();
  const [view, setView] = useState<View | null>(null);
  const [started, setStarted] = useState(false);
  const [answered, setAnswered] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const shownAt = useRef<number | null>(null);

  useEffect(() => {
    if (!me) return;
    api
      .placement()
      .then((v) => {
        setView(v);
        setAnswered(new Set(v.answered));
        setResult(v.result ?? null);
        setStarted(v.answered.length > 0);
      })
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Test yüklenemedi."));
  }, [me]);

  const current = view?.questions.find((q) => !answered.has(q.id));

  useEffect(() => {
    shownAt.current = performance.now();
  }, [current?.id]);

  if (!me) return <Screen><Loading /></Screen>;

  async function choose(answer: string) {
    if (!current || busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.placementAnswer({ question_id: current.id, answer, duration_ms: elapsedSince(shownAt.current) });
      const next = new Set(answered).add(current.id);
      setAnswered(next);
      if (view && view.questions.every((q) => next.has(q.id))) {
        setResult(await api.placementComplete());
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gönderilemedi, tekrar dene.");
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <Screen title="Başlangıç seviyen">
        <Card className="flex flex-col gap-3">
          <p className="text-3xl font-semibold">{LEVEL_TEXT[result.cefr_estimate] ?? result.cefr_estimate}</p>
          <p className="text-sm leading-relaxed text-subtle">
            Bu bir tahmin, not değil. Çalışmalarını bu seviyeden başlatacağız; sen ilerledikçe
            sistem seni daha iyi tanıyacak ve planı her hafta güncelleyecek.
          </p>
        </Card>
        <Button onClick={() => router.replace("/panel")}>Panele geç</Button>
      </Screen>
    );
  }

  if (!view) {
    return (
      <Screen title="Seviye testi">
        <ErrorText message={error} />
        {!error && <Loading />}
      </Screen>
    );
  }

  if (!started) {
    return (
      <Screen title="Seviye testi">
        <Card className="flex flex-col gap-3 leading-relaxed">
          <p>Seni hangi seviyeden başlatacağımızı bulmak için {view.questions.length} kısa soru.</p>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            <li>Yaklaşık 10 dakika sürer.</li>
            <li>Sözlük ya da çeviri kullanma; bilmiyorsan “Bilmiyorum” de. Tahmin etmek sonucu bozar.</li>
            <li>Doğru cevaplar test sırasında gösterilmez.</li>
          </ul>
        </Card>
        <Button onClick={() => setStarted(true)}>Başla</Button>
      </Screen>
    );
  }

  return (
    <Screen title="Seviye testi">
      <TestProgress done={answered.size} total={view.questions.length} />

      {current && (
        <div className="flex flex-col gap-4">
          {current.passage && (
            <Card>
              <p className="leading-relaxed" lang="en">
                {current.passage}
              </p>
            </Card>
          )}
          <BlankPrompt text={current.prompt} />
          <TestOptions options={current.options} busy={busy} onChoose={choose} />
        </div>
      )}
      <ErrorText message={error} />
    </Screen>
  );
}
