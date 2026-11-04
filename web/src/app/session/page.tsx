"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ActivityQueue } from "@/components/activity-runner";
import { ErrorText, Loading, Screen } from "@/components/ui";
import { ApiError, api, type SessionView } from "@/lib/api";
import { useMe } from "@/lib/use-me";

export default function SessionPage() {
  const me = useMe("app");
  const [session, setSession] = useState<SessionView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me) return;
    api
      .sessionToday()
      .then(setSession)
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Oturum yüklenemedi."));
  }, [me]);

  if (!me) return <Screen><Loading /></Screen>;

  return (
    <Screen title="Bugünün oturumu">
      <Link href="/panel" className="-mt-4 text-sm text-subtle underline-offset-4 hover:underline">
        ← Panele dön
      </Link>
      <ErrorText message={error} />

      {!session && !error && <Loading label="Oturumun hazırlanıyor, birkaç saniye sürebilir…" />}

      {session && (
        <ActivityQueue
          activities={session.activities}
          doneMessage={
            <>
              <p className="text-lg font-medium">Bugünlük bu kadar.</p>
              <p className="text-sm text-subtle">Yarın tekrar edilecek öğeler sana göre seçilecek.</p>
              <Link href="/panel" className="text-accent underline-offset-4 hover:underline">
                Panele dön
              </Link>
            </>
          }
        />
      )}
    </Screen>
  );
}
