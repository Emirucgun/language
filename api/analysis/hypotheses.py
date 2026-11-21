"""H1 ve H3 analizi: olay tablosundan okur, hiçbir şey yazmaz.

    cd api
    uv run python -m analysis.hypotheses

Düz betik, `# %%` hücreleriyle: VS Code not defteri gibi açar, Jupyter kurmak gerekmez.

H1 için eşik %70 ve taban önemlidir: hedef oranı kontrol oranına yakınsa öğrenci o öğeleri
zaten biliyordu ya da tahmin ediyordu, uygulama bir şey öğretmemiştir. Bir öğrencinin
cevapları birbirinden bağımsız değildir; güven sınırı bu yüzden iyimserdir, öğrenci
ortalamasıyla birlikte okunur.
"""

# %% Hesaplar
import os
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from math import comb
from statistics import mean

from eval.stats import lower_bound
from scripts.sheets import utf8_output

H1_TARGET = 0.70
MIN_USERS = 5  # altında sonuç yalnızca akışın çalıştığını gösterir


@dataclass(frozen=True, slots=True)
class RetentionAnswer:
    user_id: str
    group: str
    correct: bool


@dataclass(frozen=True, slots=True)
class H1:
    target_correct: int
    target_total: int
    control_correct: int
    control_total: int
    users: int
    user_mean: float | None

    @property
    def target_rate(self) -> float | None:
        return self.target_correct / self.target_total if self.target_total else None

    @property
    def control_rate(self) -> float | None:
        return self.control_correct / self.control_total if self.control_total else None

    @property
    def target_lower(self) -> float | None:
        return lower_bound(self.target_correct, self.target_total) if self.target_total else None

    @property
    def net(self) -> float | None:
        """Tabanın üstünde kalan: uygulamanın katkısına en yakın sayı."""
        if self.target_rate is None or self.control_rate is None:
            return None
        return self.target_rate - self.control_rate


def h1(answers: Iterable[RetentionAnswer]) -> H1:
    rows = list(answers)
    targets = [a for a in rows if a.group == "target"]
    controls = [a for a in rows if a.group == "control"]
    by_user: dict[str, list[bool]] = defaultdict(list)
    for a in targets:
        by_user[a.user_id].append(a.correct)
    return H1(
        target_correct=sum(a.correct for a in targets),
        target_total=len(targets),
        control_correct=sum(a.correct for a in controls),
        control_total=len(controls),
        users=len(by_user),
        user_mean=mean(sum(v) / len(v) for v in by_user.values()) if by_user else None,
    )


@dataclass(frozen=True, slots=True)
class PrePost:
    user_id: str
    pre_form: str
    pre_score: float
    post_score: float

    @property
    def gain(self) -> float:
        return self.post_score - self.pre_score


@dataclass(frozen=True, slots=True)
class H3:
    pairs: int
    mean_gain: float | None
    improved: int
    worsened: int
    p_value: float | None
    gain_by_first_form: dict[str, float]


def sign_test(wins: int, losses: int) -> float:
    """Tek yönlü işaret testi: artış ve düşüş eşit olasılıklıysa bu kadar artış görme şansı."""
    n = wins + losses
    if n == 0:
        return 1.0
    return sum(comb(n, i) for i in range(wins, n + 1)) / 2**n


def h3(pairs: Iterable[PrePost]) -> H3:
    rows = list(pairs)
    improved = sum(p.gain > 0 for p in rows)
    worsened = sum(p.gain < 0 for p in rows)
    by_form: dict[str, list[float]] = defaultdict(list)
    for p in rows:
        by_form[p.pre_form].append(p.gain)
    return H3(
        pairs=len(rows),
        mean_gain=mean(p.gain for p in rows) if rows else None,
        improved=improved,
        worsened=worsened,
        p_value=sign_test(improved, worsened) if rows else None,
        gain_by_first_form={form: mean(gains) for form, gains in sorted(by_form.items())},
    )


# %% Veri
RETENTION_SQL = """
    SELECT user_id::text, payload->>'group', (payload->>'correct')::boolean
    FROM learning.events
    WHERE type = 'retention_test_answer'
      AND (payload->>'group' = 'control' OR (payload->>'days_since_study')::int >= 14)
"""

PRE_POST_SQL = """
    SELECT pre.user_id::text, t.form, (pre.payload->>'score')::float,
           (post.payload->>'score')::float
    FROM learning.events pre
    JOIN learning.events post
      ON post.user_id = pre.user_id AND post.type = 'fixed_test_completed'
      AND post.payload->>'phase' = 'post'
    JOIN content.fixed_tests t ON t.id = (pre.payload->>'test_id')::int
    WHERE pre.type = 'fixed_test_completed'
      AND pre.payload->>'phase' IS DISTINCT FROM 'post'
"""


def _percent(value: float | None) -> str:
    return "yok" if value is None else f"%{value * 100:.1f}"


def report_h1(result: H1) -> list[str]:
    lines = [
        f"H1 hatırlama: {result.users} öğrenci, {result.target_total} hedef cevap",
        f"  Hedef: {_percent(result.target_rate)} (eşik %{H1_TARGET * 100:.0f}, "
        f"alt sınır {_percent(result.target_lower)})",
        f"  Öğrenci ortalaması: {_percent(result.user_mean)}",
        f"  Taban (kontrol): {_percent(result.control_rate)}, {result.control_total} cevap",
        f"  Tabanın üstü: {_percent(result.net)}",
    ]
    if result.users < MIN_USERS:
        lines.append(f"  Uyarı: {MIN_USERS} öğrenciden az; karar için kullanma.")
    return lines


def report_h3(result: H3) -> list[str]:
    gain = "yok" if result.mean_gain is None else f"{result.mean_gain * 100:+.1f} puan"
    p_value = "yok" if result.p_value is None else f"{result.p_value:.3f}"
    lines = [
        f"H3 ön ve son test: {result.pairs} öğrenci",
        f"  Ortalama artış: {gain}",
        f"  Artan {result.improved}, düşen {result.worsened}, işaret testi p = {p_value}",
    ]
    for form, value in result.gain_by_first_form.items():
        lines.append(f"  {form} formuyla başlayanlar: {value * 100:+.1f} puan")
    if result.pairs < MIN_USERS:
        lines.append(f"  Uyarı: {MIN_USERS} öğrenciden az; karar için kullanma.")
    return lines


# %% Sonuç
def main() -> None:
    import psycopg
    from dotenv import load_dotenv

    utf8_output()
    load_dotenv()
    url = os.environ["DATABASE_URL"].replace("+psycopg", "")
    with psycopg.connect(url) as conn:
        retention = [RetentionAnswer(*row) for row in conn.execute(RETENTION_SQL)]
        pairs = [PrePost(*row) for row in conn.execute(PRE_POST_SQL)]
    print("\n".join([*report_h1(h1(retention)), "", *report_h3(h3(pairs))]))


if __name__ == "__main__":
    main()
