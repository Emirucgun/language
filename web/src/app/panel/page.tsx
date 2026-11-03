"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

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

  if (!me) return <Screen><Loading /></Screen>;

  async function logout() {
    await api.logout();
    router.replace("/login");
  }

  return (
    <Screen title={me.display_name ? `Merhaba ${me.display_name}` : "Merhaba"}>
      <Card className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Bugünün oturumu</h2>
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-subtle">Önerilen</span>
        </div>
        <p className="text-sm text-subtle">
          Günlük oturumun {me.daily_minutes ?? 15} dakikalık olacak. Oturum üretimi henüz hazır değil;
          şimdilik aşağıdan yazma pratiği yapabilirsin.
        </p>
        <Button disabled>Yakında</Button>
      </Card>

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
    </Screen>
  );
}
