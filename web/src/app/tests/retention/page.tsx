"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { BlankPrompt, TestOptions, TestProgress } from "@/components/test-question";
import { Button, Card, ErrorText, Loading, Screen } from "@/components/ui";
import { ApiError, api, type Schemas } from "@/lib/api";
import { useMe } from "@/lib/use-me";

type View = Schemas["RetentionView"];
type Result = Schemas["RetentionResult"];

/**
 * 14 gün hatırlama testi. Ölçümdür: doğru cevap gösterilmez, tekrar planı değişmez.
 * Yarıda bırakılırsa kaldığı sorudan sürer.
 */
export default function RetentionTestPage() {
  const me = useMe("app");
  const [view, setView] = useState<View | null>(null);
  const [answered, setAnswered] = useState<Set<string>>(new Set());
  const [started, setStarted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const shownAt = useRef<number | null>(null);

  useEffect(() => {
    if (!me) return;
    api
      .retentionTest()
      .then((v) => {
        setView(v);
        setAnswered(new Set(v.answered));
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
    const duration = shownAt.current === null ? null : Math.round(performance.now() - shownAt.current);
    try {
      const outcome = await api.retentionAnswer({ question_id: current.id, answer, duration_ms: duration });
      setAnswered(new Set(answered).add(current.id));
      if (outcome.done) setResult(outcome);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gönderilemedi, tekrar dene.");
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <Screen title="Test bitti">
        <Card className="flex flex-col gap-3">
          <p className="text-3xl font-semibold">
            {result.correct} / {result.total}
          </p>
          <p className="text-sm leading-relaxed text-subtle">
            Çalıştığın kelimelerden bu kadarını hatırladın. Bu bir not değil; öğrenme planının işe
            yarayıp yaramadığını anlamamıza yardım ediyor.
          </p>
        </Card>
        <Link
          href="/panel"
          className="flex min-h-12 items-center justify-center rounded-xl bg-foreground px-4 font-medium text-background hover:opacity-90"
        >
          Panele dön
        </Link>
      </Screen>
    );
  }

  if (!view) {
    return (
      <Screen title="Hatırlama testi">
        <ErrorText message={error} />
        {!error && <Loading />}
      </Screen>
    );
  }

  if (!started) {
    return (
      <Screen title="Hatırlama testi">
        <Card className="flex flex-col gap-3 leading-relaxed">
          <p>İki hafta önce çalıştığın kelimeleri hatırlıyor musun? {view.questions.length} kısa soru.</p>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            <li>Yaklaşık 3 dakika sürer.</li>
            <li>Bazı sorular henüz çalışmadığın kelimelerden; bilmemen normal.</li>
            <li>Sözlük kullanma; bilmiyorsan “Bilmiyorum” de.</li>
            <li>Doğru cevaplar gösterilmez.</li>
          </ul>
        </Card>
        <Button onClick={() => setStarted(true)}>Başla</Button>
      </Screen>
    );
  }

  return (
    <Screen title="Hatırlama testi">
      <TestProgress done={answered.size} total={view.questions.length} />
      {current && (
        <div className="flex flex-col gap-4">
          <p className="text-sm text-subtle">{current.sentence_tr}</p>
          <BlankPrompt text={current.sentence_en} lang="en" />
          <TestOptions options={current.options} busy={busy} onChoose={choose} />
        </div>
      )}
      <ErrorText message={error} />
    </Screen>
  );
}
