"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { Button, ErrorText, Loading, Screen } from "@/components/ui";
import { ApiError, api, type Schemas } from "@/lib/api";
import { nextPath, useMe } from "@/lib/use-me";

type Goal = Schemas["GoalSet"]["goal"];
type Skill = Schemas["GoalSet"]["weak_skills"][number];
type Interest = Schemas["GoalSet"]["interests"][number];

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
// Serbest metin değil: ilgi alanı prompt'a girer (enjeksiyon ve uygunsuz içerik kapısı olurdu).
const INTERESTS: { value: Interest; label: string }[] = [
  { value: "football", label: "Futbol" },
  { value: "sports", label: "Spor" },
  { value: "music", label: "Müzik" },
  { value: "films", label: "Film" },
  { value: "food", label: "Yemek" },
  { value: "travel", label: "Seyahat" },
  { value: "books", label: "Kitap" },
  { value: "technology", label: "Teknoloji" },
  { value: "games", label: "Oyun" },
  { value: "animals", label: "Hayvanlar" },
  { value: "nature", label: "Doğa" },
  { value: "shopping", label: "Alışveriş" },
];

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
  const [interests, setInterests] = useState<Interest[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!me) return <Screen><Loading /></Screen>;

  function toggleInterest(value: Interest) {
    setInterests((list) => (list.includes(value) ? list.filter((x) => x !== value) : [...list, value]));
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!goal) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.goals({ goal, daily_minutes: minutes, weak_skills: skills, interests });
      router.replace(nextPath(updated));
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

        <fieldset className="flex flex-col gap-2">
          <legend className="text-sm font-medium">İlgi alanların (örnekler bunlardan seçilecek)</legend>
          <div className="flex flex-wrap gap-2">
            {INTERESTS.map((interest) => (
              <Choice
                key={interest.value}
                selected={interests.includes(interest.value)}
                onClick={() => toggleInterest(interest.value)}
              >
                {interest.label}
              </Choice>
            ))}
          </div>
        </fieldset>

        <ErrorText message={error} />
        <Button type="submit" disabled={!goal || busy}>
          Kaydet ve başla
        </Button>
      </form>
    </Screen>
  );
}
