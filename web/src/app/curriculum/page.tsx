"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card, ErrorText, Loading, Screen } from "@/components/ui";
import { ApiError, api, type Schemas } from "@/lib/api";
import { useMe } from "@/lib/use-me";

type Curriculum = Schemas["CurriculumView"];

/** Müfredat, bir kitabın içindekiler bölümü gibi (blueprint, Bölüm 3, adım 5). */
export default function CurriculumPage() {
  const me = useMe("app");
  const [plan, setPlan] = useState<Curriculum | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me) return;
    api
      .curriculum()
      .then((p) => {
        setPlan(p);
        setOpen(p.current_week);
      })
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Plan yüklenemedi."));
  }, [me]);

  if (!me) return <Screen><Loading /></Screen>;

  return (
    <Screen title="Planın">
      <Link href="/panel" className="-mt-4 text-sm text-subtle underline-offset-4 hover:underline">
        ← Panele dön
      </Link>
      <ErrorText message={error} />
      {!plan && !error && <Loading label="Planın hazırlanıyor, birkaç saniye sürebilir…" />}

      {plan && (
        <>
          <p className="leading-relaxed">{plan.summary_tr}</p>
          <p className="text-sm text-subtle">{plan.estimate_tr}</p>

          <ol className="flex flex-col gap-2">
            {plan.weeks.map((week) => {
              const expanded = open === week.week;
              return (
                <li key={week.week}>
                  <Card className={week.current ? "border-accent" : ""}>
                    <button
                      type="button"
                      onClick={() => setOpen(expanded ? null : week.week)}
                      aria-expanded={expanded}
                      className="flex w-full items-center justify-between gap-3 text-left"
                    >
                      <span className="flex flex-col">
                        <span className="text-xs text-subtle">
                          {week.week}. hafta{week.current ? " · şu an buradasın" : ""}
                        </span>
                        <span className="font-medium">{week.focus_tr}</span>
                      </span>
                      <span className="shrink-0 text-sm text-subtle">{week.item_count} öğe</span>
                    </button>

                    {expanded && (
                      <div className="mt-3 flex flex-col gap-3 border-t border-line pt-3">
                        <div>
                          <p className="text-xs font-medium text-subtle">Hafta sonunda</p>
                          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm">
                            {week.can_do_tr.map((c) => (
                              <li key={c}>{c}</li>
                            ))}
                          </ul>
                        </div>
                        {week.items_en.length > 0 && (
                          <p className="text-sm" lang="en">
                            {week.items_en.join(" · ")}
                          </p>
                        )}
                      </div>
                    )}
                  </Card>
                </li>
              );
            })}
          </ol>
        </>
      )}
    </Screen>
  );
}
