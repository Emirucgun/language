"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { ErrorText, Loading, Screen } from "@/components/ui";
import { WritingExercise } from "@/components/writing-exercise";
import { ApiError, api, type WritingTask } from "@/lib/api";
import { useMe } from "@/lib/use-me";

// Ek çalışma: serbest yazma. Görev şablonla, öğe tekrar motorundan gelir.
export default function WritingPracticePage() {
  const me = useMe("app");
  const [task, setTask] = useState<WritingTask | null>(null);
  const [round, setRound] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const recorded = useRef(false);

  const fetchTask = useCallback(() => {
    api
      .writingTask()
      .then(setTask)
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Görev yüklenemedi."));
  }, []);

  useEffect(() => {
    if (!me) return;
    fetchTask();
    // H7: öneri ile seçim ayrı kaydedilir (tekrar/okuma için sunucu yazar, yazma için burada).
    if (!recorded.current) {
      recorded.current = true;
      api
        .recommendation()
        .then((r) =>
          api.event({
            type: "extra_activity_chosen",
            payload: { recommended_kind: r.recommended, chosen_kind: "writing" },
          }),
        )
        .catch(() => undefined);
    }
  }, [me, fetchTask]);

  if (!me) return <Screen><Loading /></Screen>;

  function next() {
    setTask(null);
    setError(null);
    setRound((r) => r + 1);
    fetchTask();
  }

  return (
    <Screen title="Yazma">
      <Link href="/panel" className="-mt-4 text-sm text-subtle underline-offset-4 hover:underline">
        ← Panele dön
      </Link>
      {!task && !error && <Loading label="Görev hazırlanıyor…" />}
      <ErrorText message={error} />
      {task && (
        <WritingExercise
          key={round}
          taskTr={task.task_tr}
          send={(text) => api.feedback({ text, task: task.task, target_item_ids: task.target_item_ids })}
          onFinished={next}
          finishLabel="Yeni cümle"
        />
      )}
    </Screen>
  );
}
