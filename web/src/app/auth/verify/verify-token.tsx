"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Card, Loading } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { nextPath } from "@/lib/use-me";

export function VerifyToken() {
  const token = useSearchParams().get("token");
  const router = useRouter();
  const [error, setError] = useState<string | null>(token ? null : "Bağlantı eksik.");
  // Bağlantı tek kullanımlık: geliştirme modunda efekt iki kez çalışsa da bir kez gönder.
  const sent = useRef(false);

  useEffect(() => {
    if (!token || sent.current) return;
    sent.current = true;
    api
      .verifyLogin(token)
      .then((me) => router.replace(nextPath(me)))
      .catch((err: unknown) =>
        setError(err instanceof ApiError ? err.message : "Bir sorun oldu, tekrar dene."),
      );
  }, [token, router]);

  if (!error) return <Loading label="Bağlantı doğrulanıyor…" />;
  return (
    <Card>
      <p role="alert">{error}</p>
      <Link href="/login" className="mt-3 inline-block text-accent underline-offset-4 hover:underline">
        Yeni bağlantı iste
      </Link>
    </Card>
  );
}
