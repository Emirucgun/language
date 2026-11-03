"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, api, type Me } from "./api";

/** Kullanıcının bir sonraki zorunlu adımı: onam → hedef → panel. */
export function nextPath(me: Me): string {
  if (!me.consent_done) return "/onboarding/consent";
  if (!me.goal) return "/onboarding/goals";
  return "/panel";
}

/**
 * Giriş yapmış kullanıcıyı yükler. Giriş yoksa /login'e, sayfa bu kullanıcı için
 * henüz açılmamışsa (ör. onamdan önce panel) doğru adıma yönlendirir.
 */
export function useMe(page: "consent" | "goals" | "app"): Me | null {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then((user) => {
        if (cancelled) return;
        const required = nextPath(user);
        const allowed =
          page === "consent" ||
          (page === "goals" && user.consent_done) ||
          (page === "app" && required === "/panel");
        if (allowed) setMe(user);
        else router.replace(required);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        // 401 → giriş; diğer hatalar → ana sayfa, orada "tekrar dene" gösterilir.
        router.replace(err instanceof ApiError && err.status === 401 ? "/login" : "/");
      });
    return () => {
      cancelled = true;
    };
  }, [page, router]);

  return me;
}
