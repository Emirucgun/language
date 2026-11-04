"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { FeedbackPanel } from "@/components/feedback-panel";
import { Button, Card, ErrorText, Loading, Screen } from "@/components/ui";
import { ApiError, api, type Schemas } from "@/lib/api";
import { useMe } from "@/lib/use-me";

type Ready = Schemas["ReadyFeedbackView"];

/**
 * "Şimdilik atladık" denen cümlelerin sonradan hazırlanan geri bildirimleri, birer birer.
 * Her biri görüldüğünde `feedback_shown` yazılır ve listeden düşer.
 */
export default function ReadyFeedbackPage() {
  const me = useMe("app");
  const [items, setItems] = useState<Ready[] | null>(null);
  const [index, setIndex] = useState(0);
  const [complete, setComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me) return;
    api
      .readyFeedback()
      .then(setItems)
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Yüklenemedi."));
  }, [me]);

  if (!me) return <Screen><Loading /></Screen>;

  const current = items?.[index];

  return (
    <Screen title="Hazır geri bildirimler">
      <Link href="/panel" className="-mt-4 text-sm text-subtle underline-offset-4 hover:underline">
        ← Panele dön
      </Link>
      <ErrorText message={error} />
      {!items && !error && <Loading />}

      {items && current && (
        <>
          <p className="text-sm text-subtle">
            Daha önce yazdığın cümle · {index + 1} / {items.length}
          </p>
          <FeedbackPanel
            key={current.feedback.feedback_id}
            text={current.learner_text}
            view={current.feedback}
            onComplete={() => setComplete(true)}
          />
          {complete && (
            <Button
              onClick={() => {
                setComplete(false);
                setIndex(index + 1);
              }}
            >
              {index + 1 < items.length ? "Sonraki" : "Bitir"}
            </Button>
          )}
        </>
      )}

      {items && !current && (
        <Card>
          <p>Bekleyen geri bildirimin kalmadı.</p>
        </Card>
      )}
    </Screen>
  );
}
