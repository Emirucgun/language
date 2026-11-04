"""Günlük kota: öğrencinin ayırdığı süreden günde kaç tekrar ve yeni öğe çıkar.

Tek tanım: hem oturum üretimi hem müfredat kapasitesi buradan okur.
"""

from dataclasses import dataclass

DEFAULT_MINUTES = 15


@dataclass(frozen=True, slots=True)
class DailyQuota:
    max_reviews: int
    max_new: int


def daily_quota(daily_minutes: int | None) -> DailyQuota:
    minutes = daily_minutes or DEFAULT_MINUTES
    if minutes <= 10:
        return DailyQuota(max_reviews=4, max_new=2)
    if minutes <= 20:
        return DailyQuota(max_reviews=6, max_new=3)
    return DailyQuota(max_reviews=8, max_new=4)
