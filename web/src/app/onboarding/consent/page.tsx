"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Button, Card, ErrorText, Loading, Screen, inputClass } from "@/components/ui";
import { ApiError, CONSENT_VERSION, api } from "@/lib/api";
import { nextPath, useMe } from "@/lib/use-me";

// TASLAK metin: KVKK/GDPR metni pilot öncesi hukuken gözden geçirilecek (blueprint, Bölüm 2).
export default function ConsentPage() {
  const me = useMe("consent");
  const router = useRouter();
  const [adult, setAdult] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!me) return <Screen><Loading /></Screen>;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const updated = await api.consent({
        consent_version: CONSENT_VERSION,
        is_adult_confirmed: true,
        display_name: name.trim() || null,
      });
      router.replace(nextPath(updated));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Bir sorun oldu, tekrar dene.");
      setBusy(false);
    }
  }

  return (
    <Screen title="Başlamadan önce">
      <Card className="flex flex-col gap-3 text-sm leading-relaxed">
        <p>Bu bir pilot çalışma. Seni daha iyi tanıyıp çalışmanı kişiselleştirmek için şunları kaydediyoruz:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>E-posta adresin ve istersen adın,</li>
          <li>hedefin, ilgi alanların ve çalıştığın süre,</li>
          <li>cevapların ve yazdığın cümleler.</li>
        </ul>
        <p>
          Yazdığın cümleler geri bildirim için bir yapay zekâ servisine gönderilir; adın ve e-postan
          gönderilmez. Verilerini istediğin zaman sildirebilirsin.
        </p>
      </Card>

      <form onSubmit={submit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-2">
          <span className="text-sm font-medium">Sana nasıl hitap edelim? (isteğe bağlı)</span>
          <input value={name} onChange={(e) => setName(e.target.value)} maxLength={80} className={inputClass} />
        </label>
        <label className="flex items-start gap-3">
          <input type="checkbox" checked={adult} onChange={(e) => setAdult(e.target.checked)} className="mt-1 size-5 shrink-0" />
          <span>18 yaşından büyüğüm.</span>
        </label>
        <label className="flex items-start gap-3">
          <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} className="mt-1 size-5 shrink-0" />
          <span>Yukarıdaki metni okudum ve verilerimin bu amaçla işlenmesini kabul ediyorum.</span>
        </label>
        <ErrorText message={error} />
        <Button type="submit" disabled={!adult || !agreed || busy}>
          Devam et
        </Button>
      </form>
    </Screen>
  );
}
