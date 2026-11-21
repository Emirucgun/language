"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, api, type Me } from "./api";

/** Kullanıcının bir sonraki zorunlu adımı: onam → hedef → yerleştirme testi → panel. */
export function nextPath(me: Me): string {
  if (!me.consent_done) return "/onboarding/consent";
  if (!me.goal) return "/onboarding/goals";
  if (!me.placement_done) return "/onboarding/placement";
  return "/panel";
}

/** Girişten sonraki ilk ekran: inceleyen öğrenci akışını bitirmek zorunda değil. */
export function landingPath(me: Me): string {
  return me.role === "reviewer" ? "/review" : nextPath(me);
}

/**
 * Giriş yapmış kullanıcıyı yükler. Giriş yoksa /login'e, sayfa bu kullanıcı için
 * henüz açılmamışsa (ör. onamdan önce panel) doğru adıma yönlendirir.
 */
export function useMe(page: "consent" | "goals" | "placement" | "app" | "review"): Me | null {
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
          (page === "placement" && user.consent_done && !!user.goal) ||
          (page === "app" && required === "/panel") ||
          (page === "review" && user.role === "reviewer");
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
