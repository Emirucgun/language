"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card, ErrorText, Loading, Screen } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useMe } from "@/lib/use-me";

// Sunucudaki WeeklyMetrics (api/app/reports/service.py) + yeniden planlama alanları.
type Metrics = {
  week_start: string;
  active_days: number;
  sessions_completed: number;
  new_items: number;
  consolidated_items: number;
  answers: number;
  success_rate: number | null;
  minutes_by_skill: Record<string, number>;
  top_error: { code: string; name_tr: string; explanation_tr: string; count: number } | null;
  plan_changed: boolean;
  plan_change_tr?: string | null;
};

const SKILL_TR: Record<string, string> = {
  vocabulary: "Kelime",
  reading: "Okuma",
  listening: "Dinleme",
  writing: "Yazma",
};

function weekLabel(isoMonday: string): string {
  const start = new Date(`${isoMonday}T00:00:00`);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  const fmt = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long" });
  return `${fmt.format(start)} – ${fmt.format(end)}`;
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <Card className="flex flex-col gap-1">
      <span className="text-2xl font-semibold">{value}</span>
      <span className="text-sm text-subtle">{label}</span>
    </Card>
  );
}

export default function ReportPage() {
  const me = useMe("app");
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [missing, setMissing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me) return;
    api
      .latestReport()
      .then((r) => {
        setMetrics(r.metrics as unknown as Metrics);
        void api.event({ type: "report_viewed", payload: {} });
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) setMissing(true);
        else setError(err instanceof ApiError ? err.message : "Rapor yüklenemedi.");
      });
  }, [me]);

  if (!me) return <Screen><Loading /></Screen>;

  const minutes = metrics ? Object.entries(metrics.minutes_by_skill).filter(([, m]) => m > 0) : [];
  const totalMinutes = minutes.reduce((sum, [, m]) => sum + m, 0);

  return (
    <Screen title="Haftalık rapor">
      <Link href="/panel" className="-mt-4 text-sm text-subtle underline-offset-4 hover:underline">
        ← Panele dön
      </Link>
      <ErrorText message={error} />
      {missing && <Card><p>İlk raporun pazar akşamı hazır olacak.</p></Card>}
      {!metrics && !missing && !error && <Loading />}

      {metrics && (
        <>
          <p className="text-subtle">{weekLabel(metrics.week_start)}</p>

          <div className="grid grid-cols-2 gap-2">
            <Stat value={String(metrics.new_items)} label="yeni öğe öğrendin" />
            <Stat value={String(metrics.consolidated_items)} label="öğe kalıcılaştı" />
            <Stat
              value={metrics.success_rate == null ? "–" : `%${Math.round(metrics.success_rate * 100)}`}
              label="tekrar başarısı"
            />
            <Stat value={`${metrics.active_days} / 7`} label="gün çalıştın" />
          </div>

          {minutes.length > 0 && (
            <Card className="flex flex-col gap-2">
              <p className="font-medium">Zamanını nereye ayırdın</p>
              {minutes.map(([skill, m]) => (
                <div key={skill} className="flex items-center gap-3 text-sm">
                  <span className="w-16 shrink-0">{SKILL_TR[skill] ?? skill}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className="h-full bg-accent" style={{ width: `${(m / totalMinutes) * 100}%` }} />
                  </div>
                  <span className="w-14 shrink-0 text-right text-subtle">{m.toFixed(1)} dk</span>
                </div>
              ))}
            </Card>
          )}

          {metrics.top_error && (
            <Card className="flex flex-col gap-1 bg-muted">
              <p className="text-xs text-subtle">Bu haftanın en sık hatası ({metrics.top_error.count} kez)</p>
              <p className="font-medium">{metrics.top_error.name_tr}</p>
              <p className="text-sm leading-relaxed">{metrics.top_error.explanation_tr}</p>
            </Card>
          )}

          <Card className="flex flex-col gap-1">
            <p className="font-medium">Planın</p>
            <p className="text-sm leading-relaxed">
              {metrics.plan_changed && metrics.plan_change_tr
                ? metrics.plan_change_tr
                : "Bu hafta çalışma olmadığı için plan aynı kaldı."}
            </p>
            <Link href="/curriculum" className="text-sm text-accent underline-offset-4 hover:underline">
              Güncel planı gör
            </Link>
          </Card>
        </>
      )}
    </Screen>
  );
}
