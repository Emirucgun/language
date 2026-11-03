"""Giriş bağlantısı gönderimi. E-posta servisi henüz seçilmedi (Technical MVP, Bölüm 10).

Yerelde bağlantı loga yazılır; servis seçilince yalnızca yeni bir `EmailSender` eklenir.
"""

from typing import Protocol

import structlog

log = structlog.get_logger()


class EmailSender(Protocol):
    def send_login_link(self, email: str, url: str) -> None: ...


class ConsoleEmailSender:
    def send_login_link(self, email: str, url: str) -> None:
        log.info("login_link", email=email, url=url)
