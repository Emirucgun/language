"""Altın set raporu. Prompt ya da model değişikliği bu rapor olmadan birleşmez.

    cd api
    uv run python -m eval.golden --purpose feedback           # yalnızca dev bölmesi
    uv run python -m eval.golden --purpose feedback --final   # dev ve test, ayrı ayrı

`test` bölmesi yalnızca nihai ölçüm içindir: prompt ayarlarken görülen cümle ölçümü geçersiz
kılar. CI bu betiği çalıştırmaz; `--final` CI'da reddedilir.

Gerçek API çağrısı yapar ve ücretlidir. Veritabanına hiçbir şey bırakmaz.
"""

import argparse
import json
import os
import sys
from collections.abc import Callable
from dataclasses import fields
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app import models  # noqa: F401 - tüm tabloları kaydeder
from app.config import settings
from app.deps import get_llm_client
from app.feedback import prompt as feedback_prompt
from app.feedback.llm_schema import WritingFeedback
from app.feedback.service import active_tags
from app.llm.client import LLMClient
from app.llm.service import Prompt, generate_structured
from app.reports.models import Review
from app.validator.core import Lexicon, load_lexicon
from app.validator.feedback import validate_feedback
from eval.scoring import Prediction, render, score
from eval.stats import upper_bound
from scripts.import_golden import DEV, TEST, GoldenCase
from scripts.sheets import utf8_output

DEFAULT_DATA = Path(__file__).resolve().parents[2] / "eval/golden/feedback.jsonl"
INJECTIONS = Path(__file__).resolve().parents[2] / "eval/golden/injection.jsonl"
DEFAULT_TASK = "Write one short sentence."  # kişi yönlendirmez: "about yourself" düzeltmeyi bozdu
MIN_JUDGMENTS = 150

Evaluate = Callable[[GoldenCase], Prediction]


def load_cases(path: Path) -> list[GoldenCase]:
    names = {f.name for f in fields(GoldenCase)}
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    return [GoldenCase(**{k: v for k, v in row.items() if k in names}) for row in rows]


def splits_to_run(final: bool, in_ci: bool) -> tuple[str, ...]:
    if final and in_ci:
        raise SystemExit("test bölmesi CI'da koşulmaz.")
    return (DEV, TEST) if final else (DEV,)


def evaluator(session: Session, client: LLMClient, lexicon: Lexicon, codes: set[str]) -> Evaluate:
    """Üretimdeki yol: aynı prompt ve doğrulayıcı. Öğrenci özeti yok, görev girdisi var."""
    static_block = feedback_prompt.static_block(session)

    def evaluate(case: GoldenCase) -> Prediction:
        prompt = Prompt(
            purpose="feedback",
            prompt_version=feedback_prompt.PROMPT_VERSION,
            static_block=static_block,
            task=feedback_prompt.task_block(
                task=case.task or DEFAULT_TASK,
                target_items=[case.target] if case.target else [],
                learner_text=case.text,
                recent_codes=[],
            ),
        )
        parsed, call = generate_structured(
            session, client, prompt=prompt, output_type=WritingFeedback, user_id=None
        )
        issues: tuple[str, ...] = ()
        if parsed is not None:
            result = validate_feedback(
                parsed, learner_text=case.text, catalog_codes=codes, lexicon=lexicon
            )
            issues = tuple(issue.code for issue in result.issues)
        return Prediction(parsed, issues, call.cost_microusd or 0, call.latency_ms or 0)

    return evaluate


def report(cases: list[GoldenCase], evaluate: Evaluate, splits: tuple[str, ...]) -> str:
    """Bölmeler birbirine karışmasın diye ayrı puanlanır."""
    sections: list[str] = []
    for split in splits:
        group = [c for c in cases if c.split == split]
        if not group:
            sections.append(f"## {split}\n\nBu bölmede cümle yok.\n")
            continue
        predictions: dict[str, Prediction] = {}
        for number, case in enumerate(group, start=1):
            print(f"{split} {number}/{len(group)}", file=sys.stderr, flush=True)
            predictions[case.id] = evaluate(case)
        sections.append(render(split, group, score(group, predictions)))
    return "\n".join(sections)


def h4_section(judged: int, wrong: int, limit: float | None) -> str:
    """H4: Işıl'ın rastgele örneklemi. "Sorun var" kayıtları şüpheli olduğu için sayılmaz."""
    if not judged:
        return "## H4\n\nHenüz rastgele örnek incelenmedi.\n"
    bound = upper_bound(wrong, judged)
    lines = [
        "## H4",
        "",
        f"Yanlış öğretme: {wrong}/{judged} (%{wrong / judged * 100:.1f}), "
        f"%95 güvenle en çok %{bound * 100:.1f}.",
    ]
    if judged < MIN_JUDGMENTS:
        lines.append(f"Örnek yetersiz: en az {MIN_JUDGMENTS} bağımsız yargı gerekir.")
    if limit is not None:
        verdict = "geçti" if bound < limit else "geçmedi"
        lines.append(f"Eşik %{limit * 100:.1f}: {verdict}.")
    return "\n".join(lines) + "\n"


def reviewed_sample(session: Session) -> tuple[int, int]:
    sample = select(func.count()).select_from(Review).where(Review.source == "sample")
    judged = session.scalar(sample) or 0
    wrong = session.scalar(sample.where(Review.verdict == "wrong_teaching")) or 0
    return judged, wrong


def main() -> None:
    utf8_output()
    parser = argparse.ArgumentParser(description="Altın set raporu (gerçek API, ücretli).")
    parser.add_argument("--purpose", choices=["feedback"], default="feedback")
    parser.add_argument("--final", action="store_true", help="test bölmesini de koşar")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, help="raporu dosyaya da yazar")
    parser.add_argument("--h4-limit", type=float, help="H4 üst sınır eşiği, örnek: 0.05")
    args = parser.parse_args()

    splits = splits_to_run(args.final, bool(os.environ.get("CI")))
    if not args.data.exists():
        sys.exit(f"Altın set yok: {args.data}. Önce: uv run python -m scripts.import_golden")
    # Enjeksiyon örnekleri Işıl'ın setinden ayrı durur: içe aktarma onları silmesin.
    cases = load_cases(args.data) + load_cases(INJECTIONS)

    engine = create_engine(settings.database_url)
    with Session(engine) as session:
        lexicon = load_lexicon(session)
        client = get_llm_client()  # sağlayıcı ayardan: LLM_PROVIDER_FEEDBACK
        evaluate = evaluator(session, client, lexicon, set(active_tags(session)))
        text = (
            report(cases, evaluate, splits)
            + "\n"
            + h4_section(*reviewed_sample(session), limit=args.h4_limit)
        )
        session.rollback()  # ölçüm iz bırakmaz
    engine.dispose()

    print(text)
    if args.output:
        args.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
