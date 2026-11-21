"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { BlankPrompt, TestOptions, TestProgress } from "@/components/test-question";
import { Button, Card, ErrorText, Loading, Screen } from "@/components/ui";
import { ApiError, api, type Schemas } from "@/lib/api";
import { useMe } from "@/lib/use-me";

type View = Schemas["PostView"];
type Result = Schemas["PostResult"];

function percent(score: number): string {
  return `%${Math.round(score * 100)}`;
}

/** Son test: seviye testinin diğer formu. Doğru cevap gösterilmez, planı değiştirmez. */
export default function PostTestPage() {
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
      .postTest()
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
    const duration = shownAt.current === null ? null : Math.round(performance.now() - shownAt.current);
    try {
      await api.postAnswer({ question_id: current.id, answer, duration_ms: duration });
      const next = new Set(answered).add(current.id);
      setAnswered(next);
      if (view && view.questions.every((q) => next.has(q.id))) {
        setResult(await api.postComplete());
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gönderilemedi, tekrar dene.");
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <Screen title="Son test bitti">
        <Card className="flex flex-col gap-3">
          <p className="text-3xl font-semibold">
            {percent(result.pre_score)} → {percent(result.score)}
          </p>
          <p className="text-sm leading-relaxed text-subtle">
            Soldaki başlangıçtaki sonucun, sağdaki bugünkü. Sorular farklıydı, bu yüzden küçük
            değişimler şans olabilir.
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
      <Screen title="Son test">
        <ErrorText message={error} />
        {!error && <Loading />}
      </Screen>
    );
  }

  if (!started) {
    return (
      <Screen title="Son test">
        <Card className="flex flex-col gap-3 leading-relaxed">
          <p>Başladığından beri ne kadar ilerledin? {view.questions.length} kısa soru.</p>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            <li>Yaklaşık 10 dakika sürer.</li>
            <li>Sorular ilk testten farklı.</li>
            <li>Sözlük ya da çeviri kullanma; bilmiyorsan “Bilmiyorum” de.</li>
            <li>Doğru cevaplar test sırasında gösterilmez.</li>
          </ul>
        </Card>
        <Button onClick={() => setStarted(true)}>Başla</Button>
      </Screen>
    );
  }

  return (
    <Screen title="Son test">
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
