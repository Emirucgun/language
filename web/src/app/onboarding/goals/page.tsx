"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, type KeyboardEvent, useState } from "react";

import { Button, ErrorText, Loading, Screen, inputClass } from "@/components/ui";
import { ApiError, api, type Schemas } from "@/lib/api";
import { useMe } from "@/lib/use-me";

type Goal = Schemas["GoalSet"]["goal"];
type Skill = Schemas["GoalSet"]["weak_skills"][number];

const GOALS: { value: Goal; label: string }[] = [
  { value: "travel", label: "Seyahat" },
  { value: "work", label: "İş" },
  { value: "school", label: "Okul" },
  { value: "daily_conversation", label: "Günlük sohbet" },
];
const MINUTES = [10, 15, 20, 30];
const SKILLS: { value: Skill; label: string }[] = [
  { value: "vocabulary", label: "Kelime" },
  { value: "reading", label: "Okuma" },
  { value: "listening", label: "Dinleme" },
  { value: "writing", label: "Yazma" },
];
const MAX_INTERESTS = 10;

function Choice({ selected, onClick, children }: { selected: boolean; onClick: () => void; children: string }) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`min-h-12 rounded-xl border px-3 text-base transition ${
        selected ? "border-foreground bg-foreground text-background" : "border-line bg-card hover:bg-muted"
      }`}
    >
      {children}
    </button>
  );
}

export default function GoalsPage() {
  const me = useMe("goals");
  const router = useRouter();
  const [goal, setGoal] = useState<Goal | null>(null);
  const [minutes, setMinutes] = useState(15);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [interests, setInterests] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!me) return <Screen><Loading /></Screen>;

  function addInterest() {
    const value = draft.trim().toLowerCase();
    if (value && !interests.includes(value) && interests.length < MAX_INTERESTS) {
      setInterests([...interests, value]);
    }
    setDraft("");
  }

  function onInterestKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addInterest();
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!goal) return;
    setBusy(true);
    setError(null);
    try {
      await api.goals({ goal, daily_minutes: minutes, weak_skills: skills, interests });
      router.replace("/panel");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Bir sorun oldu, tekrar dene.");
      setBusy(false);
    }
  }

  return (
    <Screen title="Hedefin">
      <form onSubmit={submit} className="flex flex-col gap-6">
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 text-sm font-medium">İngilizceyi en çok ne için istiyorsun?</legend>
          <div className="grid grid-cols-2 gap-2">
            {GOALS.map((g) => (
              <Choice key={g.value} selected={goal === g.value} onClick={() => setGoal(g.value)}>
                {g.label}
              </Choice>
            ))}
          </div>
        </fieldset>

        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 text-sm font-medium">Günde kaç dakika ayırabilirsin?</legend>
          <div className="grid grid-cols-4 gap-2">
            {MINUTES.map((m) => (
              <Choice key={m} selected={minutes === m} onClick={() => setMinutes(m)}>
                {`${m} dk`}
              </Choice>
            ))}
          </div>
        </fieldset>

        <fieldset className="flex flex-col gap-2">
          <legend className="mb-2 text-sm font-medium">Hangi alanda kendini eksik hissediyorsun?</legend>
          <div className="grid grid-cols-2 gap-2">
            {SKILLS.map((s) => (
              <Choice
                key={s.value}
                selected={skills.includes(s.value)}
                onClick={() =>
                  setSkills(skills.includes(s.value) ? skills.filter((x) => x !== s.value) : [...skills, s.value])
                }
              >
                {s.label}
              </Choice>
            ))}
          </div>
        </fieldset>

        <div className="flex flex-col gap-2">
          <label htmlFor="interest" className="text-sm font-medium">
            İlgi alanların (örnekler bunlardan seçilecek)
          </label>
          <div className="flex gap-2">
            <input
              id="interest"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={onInterestKey}
              placeholder="futbol, yemek, müzik…"
              className={inputClass}
            />
            <Button type="button" variant="secondary" onClick={addInterest} disabled={!draft.trim()}>
              Ekle
            </Button>
          </div>
          {interests.length > 0 && (
            <ul className="flex flex-wrap gap-2">
              {interests.map((i) => (
                <li key={i}>
                  <button
                    type="button"
                    onClick={() => setInterests(interests.filter((x) => x !== i))}
                    className="rounded-full bg-muted px-3 py-1 text-sm"
                    aria-label={`${i} kaldır`}
                  >
                    {i} ×
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <ErrorText message={error} />
        <Button type="submit" disabled={!goal || busy}>
          Kaydet ve başla
        </Button>
      </form>
    </Screen>
  );
}
