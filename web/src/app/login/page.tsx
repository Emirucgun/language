"use client";

import { type FormEvent, useState } from "react";

import { Button, Card, ErrorText, Screen, inputClass } from "@/components/ui";
import { ApiError, api } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [invite, setInvite] = useState("");
  const [showInvite, setShowInvite] = useState(false);
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const code = invite.trim().toUpperCase();
      await api.requestLogin({ email: email.trim(), invite_code: code || null });
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Bir sorun oldu, tekrar dene.");
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <Screen title="E-postanı kontrol et">
        <Card>
          <p>
            <strong>{email}</strong> adresine bir giriş bağlantısı gönderdik. Bağlantı 15 dakika
            geçerli.
          </p>
          <p className="mt-3 text-sm text-subtle">
            Gelmediyse: adresin doğru olduğundan emin ol. İlk kez geliyorsan davet kodunu da girmen
            gerekiyor.
          </p>
        </Card>
        <Button variant="ghost" onClick={() => setSent(false)}>
          Geri dön
        </Button>
      </Screen>
    );
  }

  return (
    <Screen title="Giriş">
      <p className="text-subtle">Şifre yok: e-postana tek kullanımlık bir bağlantı göndereceğiz.</p>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-2">
          <span className="text-sm font-medium">E-posta</span>
          <input
            type="email"
            required
            autoComplete="email"
            inputMode="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputClass}
          />
        </label>

        {showInvite ? (
          <label className="flex flex-col gap-2">
            <span className="text-sm font-medium">Davet kodu</span>
            <input
              value={invite}
              onChange={(e) => setInvite(e.target.value)}
              placeholder="ABCD-EFGH"
              autoCapitalize="characters"
              className={`${inputClass} font-mono tracking-widest`}
            />
          </label>
        ) : (
          <button
            type="button"
            onClick={() => setShowInvite(true)}
            className="self-start text-sm text-accent underline-offset-4 hover:underline"
          >
            İlk kez mi geliyorsun? Davet kodunu gir
          </button>
        )}

        <ErrorText message={error} />
        <Button type="submit" disabled={busy || !email}>
          {busy ? "Gönderiliyor…" : "Giriş bağlantısı gönder"}
        </Button>
      </form>
    </Screen>
  );
}
