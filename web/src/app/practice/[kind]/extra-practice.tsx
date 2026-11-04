"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ActivityQueue } from "@/components/activity-runner";
import { Button, Card, ErrorText, Loading, Screen } from "@/components/ui";
import { ApiError, api, type ActivityView } from "@/lib/api";
import { useMe } from "@/lib/use-me";

const TITLES = { recall: "Tekrar", reading: "Okuma" } as const;
type Kind = keyof typeof TITLES;

/**
 * Ek çalışma: tür öğrencinin seçimi, öğeler tekrar motorundan (vadesi gelen ve zorlanılan).
 * Seçildiği anda üretilir; kısa bir bekleme olur.
 */
export function ExtraPractice() {
  const me = useMe("app");
  const params = useParams<{ kind: string }>();
  const kind = (params.kind in TITLES ? params.kind : null) as Kind | null;
  const [activities, setActivities] = useState<ActivityView[] | null>(null);
  const [round, setRound] = useState(0);
  const [error, setError] = useState<string | null>(null);
  // Geliştirme modunda efekt iki kez çalışsa da tek üretim isteği gitsin.
  const requested = useRef(-1);

  useEffect(() => {
    if (!me || !kind || requested.current === round) return;
    requested.current = round;
    api
      .extra({ kind })
      .then((r) => setActivities(r.activities))
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Hazırlanamadı."));
  }, [me, kind, round]);

  if (!me) return <Screen><Loading /></Screen>;
  if (!kind) {
    return (
      <Screen title="Ek çalışma">
        <Card><p>Bu çalışma türü yok.</p></Card>
      </Screen>
    );
  }

  return (
    <Screen title={TITLES[kind]}>
      <Link href="/panel" className="-mt-4 text-sm text-subtle underline-offset-4 hover:underline">
        ← Panele dön
      </Link>
      <ErrorText message={error} />
      {!activities && !error && <Loading label="Senin için hazırlanıyor…" />}

      {activities && activities.length === 0 && (
        <Card>
          <p>Şu an hazırlayamadık. Biraz sonra tekrar dene ya da başka bir tür seç.</p>
        </Card>
      )}

      {activities && activities.length > 0 && (
        <ActivityQueue
          key={round}
          activities={activities}
          doneMessage={
            <>
              <p className="text-lg font-medium">Tamamlandı.</p>
              <Button
                onClick={() => {
                  setActivities(null);
                  setRound((r) => r + 1);
                }}
              >
                Bir tur daha
              </Button>
            </>
          }
        />
      )}
    </Screen>
  );
}
