"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ChoiceQuestion } from "@/components/choice-question";
import { Button, Card, ErrorText, Loading, Screen } from "@/components/ui";
import { WritingExercise } from "@/components/writing-exercise";
import { ApiError, api, type ActivityView, type SessionView } from "@/lib/api";
import { useMe } from "@/lib/use-me";

const KIND_LABEL: Record<ActivityView["kind"], string> = {
  new_item: "Yeni",
  recall: "Tekrar",
  reading: "Okuma",
  writing: "Yazma",
};

/** Yeni öğe: önce anlam ve örnekler, sonra kısa kontrol sorusu. */
function NewItemActivity({ activity, onDone }: { activity: ActivityView; onDone: (c: number) => void }) {
  const [checking, setChecking] = useState(false);
  if (!checking) {
    return (
      <div className="flex flex-col gap-4">
        <Card className="flex flex-col gap-3">
          <p className="text-2xl font-semibold" lang="en">
            {activity.item_en}
          </p>
          <p>{activity.meaning_tr}</p>
          <ul className="flex flex-col gap-3">
            {(activity.examples ?? []).map((e, i) => (
              <li key={i}>
                <p className="text-lg" lang="en">
                  {e.en}
                </p>
                <p className="text-sm text-subtle">{e.tr}</p>
              </li>
            ))}
          </ul>
        </Card>
        <Button onClick={() => setChecking(true)}>Anladım, dene</Button>
      </div>
    );
  }
  return (
    <ChoiceQuestion
      activityId={activity.id}
      question={activity.questions[0]}
      onAnswered={(correct) => onDone(correct ? 1 : 0)}
    />
  );
}

/** Okuma: metin üstte kalır, sorular sırayla. */
function ReadingActivity({ activity, onDone }: { activity: ActivityView; onDone: (c: number) => void }) {
  const [index, setIndex] = useState(0);
  const [correct, setCorrect] = useState(0);
  const question = activity.questions[index];
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <p className="text-lg leading-relaxed" lang="en">
          {activity.text_en}
        </p>
      </Card>
      <ChoiceQuestion
        key={question.id}
        activityId={activity.id}
        question={question}
        onAnswered={(ok) => {
          const total = correct + (ok ? 1 : 0);
          if (index + 1 < activity.questions.length) {
            setCorrect(total);
            setIndex(index + 1);
          } else {
            onDone(total);
          }
        }}
      />
    </div>
  );
}

function ActivityRunner({ activity, onDone }: { activity: ActivityView; onDone: (correct: number) => void }) {
  useEffect(() => {
    void api.event({ type: "activity_shown", payload: {}, activity_id: activity.id });
  }, [activity.id]);

  switch (activity.kind) {
    case "new_item":
      return <NewItemActivity activity={activity} onDone={onDone} />;
    case "recall":
      return (
        <ChoiceQuestion
          activityId={activity.id}
          question={activity.questions[0]}
          hintTr={activity.hint_tr}
          onAnswered={(ok) => onDone(ok ? 1 : 0)}
        />
      );
    case "reading":
      return <ReadingActivity activity={activity} onDone={onDone} />;
    case "writing":
      return (
        <WritingExercise
          taskTr={activity.task_tr ?? ""}
          activityId={activity.id}
          send={(text) => api.feedback({ text, activity_id: activity.id })}
          onFinished={() => onDone(0)}
          finishLabel="Devam"
        />
      );
  }
}

export default function SessionPage() {
  const me = useMe("app");
  const [session, setSession] = useState<SessionView | null>(null);
  const [finished, setFinished] = useState<Set<number>>(new Set());
  const [correct, setCorrect] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me) return;
    api
      .sessionToday()
      .then(setSession)
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Oturum yüklenemedi."));
  }, [me]);

  if (!me) return <Screen><Loading /></Screen>;

  const remaining = session?.activities.filter((a) => !a.done && !finished.has(a.id)) ?? [];
  const current = remaining[0];
  const total = session?.activities.length ?? 0;
  const position = total - remaining.length + 1;

  return (
    <Screen title="Bugünün oturumu">
      <Link href="/panel" className="-mt-4 text-sm text-subtle underline-offset-4 hover:underline">
        ← Panele dön
      </Link>
      <ErrorText message={error} />

      {!session && !error && <Loading label="Oturumun hazırlanıyor, birkaç saniye sürebilir…" />}

      {session && current && (
        <>
          <div className="flex items-center justify-between text-sm text-subtle">
            <span className="rounded-full bg-muted px-2 py-0.5">{KIND_LABEL[current.kind]}</span>
            <span aria-label="ilerleme">
              {position} / {total}
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted" aria-hidden>
            <div className="h-full bg-accent transition-all" style={{ width: `${((position - 1) / total) * 100}%` }} />
          </div>
          <ActivityRunner
            key={current.id}
            activity={current}
            onDone={(c) => {
              setCorrect((n) => n + c);
              setFinished((s) => new Set(s).add(current.id));
            }}
          />
        </>
      )}

      {session && !current && (
        <Card className="flex flex-col gap-3">
          <p className="text-lg font-medium">Bugünlük bu kadar.</p>
          {finished.size > 0 && <p className="text-subtle">Bu oturumda {correct} soruyu doğru cevapladın.</p>}
          <p className="text-sm text-subtle">Yarın tekrar edilecek öğeler sana göre seçilecek.</p>
          <Link href="/panel" className="text-accent underline-offset-4 hover:underline">
            Panele dön
          </Link>
        </Card>
      )}
    </Screen>
  );
}
