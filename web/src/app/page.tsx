"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Button, Card, Loading, Screen } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { landingPath } from "@/lib/use-me";

// Giriş noktası: kullanıcıyı durumuna göre doğru ekrana gönderir.
export default function Home() {
  const router = useRouter();
  const [failed, setFailed] = useState(false);

  const route = useCallback(() => {
    api
      .me()
      .then((me) => router.replace(landingPath(me)))
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 401) router.replace("/login");
        else setFailed(true);
      });
  }, [router]);

  useEffect(route, [route]);

  return (
    <Screen>
      {failed ? (
        <Card className="flex flex-col gap-3">
          <p role="alert">Sunucuya ulaşılamadı. Bağlantını kontrol edip tekrar dene.</p>
          <Button
            onClick={() => {
              setFailed(false);
              route();
            }}
          >
            Tekrar dene
          </Button>
        </Card>
      ) : (
        <Loading />
      )}
    </Screen>
  );
}
