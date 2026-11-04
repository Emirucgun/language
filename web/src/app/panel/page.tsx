"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button, Card, Loading, Screen } from "@/components/ui";
import { api } from "@/lib/api";
import { useMe } from "@/lib/use-me";

// Ek çalışma türleri; etkinlik üretimi gelene kadar yalnızca yazma açık.
const EXTRA = [
  { href: "/practice/writing", label: "Yazma", ready: true },
  { href: "#", label: "Tekrar", ready: false },
  { href: "#", label: "Okuma", ready: false },
  { href: "#", label: "Dinleme", ready: false },
  { href: "#", label: "Yazılı diyalog", ready: false },
];

export default function PanelPage() {
  const me = useMe("app");
  const router = useRouter();
  const [hasReport, setHasReport] = useState(false);
  const [readyCount, setReadyCount] = useState(0);

  useEffect(() => {
    if (!me) return;
    // Rapor yoksa (ilk hafta) bağlantı hiç görünmez.
    api
      .latestReport()
      .then(() => setHasReport(true))
      .catch(() => setHasReport(false));
    api
      .readyFeedback()
      .then((items) => setReadyCount(items.length))
      .catch(() => setReadyCount(0));
  }, [me]);

  if (!me) return <Screen><Loading /></Screen>;

  async function logout() {
    await api.logout();
    router.replace("/login");
  }

  return (
    <Screen title={me.display_name ? `Merhaba ${me.display_name}` : "Merhaba"}>
      {readyCount > 0 && (
        <Link
          href="/feedback"
          className="flex min-h-12 items-center justify-between rounded-xl border border-accent bg-card px-4 hover:bg-muted"
        >
          <span className="font-medium">Geri bildirimlerin hazır</span>
          <span className="text-sm text-accent">{readyCount} cümle →</span>
        </Link>
      )}

      <Card className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Bugünün oturumu</h2>
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-subtle">Önerilen</span>
        </div>
        <p className="text-sm text-subtle">
          Senin için seçilen yeni ve tekrar öğeleri, yaklaşık {me.daily_minutes ?? 15} dakika.
        </p>
        <Link
          href="/session"
          className="flex min-h-12 items-center justify-center rounded-xl bg-foreground px-4 font-medium text-background hover:opacity-90"
        >
          Başla
        </Link>
      </Card>

      <Link
        href="/curriculum"
        className="flex min-h-12 items-center justify-between rounded-xl border border-line bg-card px-4 hover:bg-muted"
      >
        <span className="font-medium">Planın</span>
        <span className="text-sm text-subtle">8 haftalık yol haritası →</span>
      </Link>

      {hasReport && (
        <Link
          href="/report"
          className="flex min-h-12 items-center justify-between rounded-xl border border-line bg-card px-4 hover:bg-muted"
        >
          <span className="font-medium">Haftalık raporun</span>
          <span className="text-sm text-subtle">bu hafta ne öğrendin →</span>
        </Link>
      )}

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">Ek çalışma</h2>
        <div className="grid grid-cols-2 gap-2">
          {EXTRA.map((x) =>
            x.ready ? (
              <Link
                key={x.label}
                href={x.href}
                className="flex min-h-14 items-center justify-center rounded-xl border border-line bg-card font-medium hover:bg-muted"
              >
                {x.label}
              </Link>
            ) : (
              <span
                key={x.label}
                className="flex min-h-14 flex-col items-center justify-center rounded-xl border border-dashed border-line text-subtle"
              >
                {x.label}
                <span className="text-xs">yakında</span>
              </span>
            ),
          )}
        </div>
      </section>

      <Button variant="ghost" onClick={logout} className="self-start">
        Çıkış yap
      </Button>

      {/* Lisans koşulu: CEFR-J kullanımı atıf gerektirir. */}
      <p className="mt-auto text-xs text-subtle">
        Kelime seviyeleri: CEFR-J Wordlist Version 1.6, Tono Laboratuvarı, Tokyo Yabancı Diller
        Üniversitesi.
      </p>
    </Screen>
  );
}
