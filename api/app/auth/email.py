"""Giriş bağlantısı gönderimi (docs/architecture/security-privacy.md).

Sağlayıcı Brevo; kod yalnızca SMTP konuşur, böylece sağlayıcı değiştirmek bir ayardır.
`SMTP_HOST` tanımlı değilse (yerel geliştirme) bağlantı loga yazılır.
"""

import smtplib
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Protocol

import structlog

from app.config import settings

log = structlog.get_logger()

SUBJECT = "Giriş bağlantın"

TEXT = """Merhaba,

İngilizce Öğretmenim'e giriş yapmak için bu bağlantıyı aç:

{url}

Bağlantı {minutes} dakika geçerli ve yalnızca bir kez kullanılabilir.
Bu isteği sen yapmadıysan bu e-postayı yok sayabilirsin; hesabına bir şey olmaz.
"""

HTML = """<!doctype html>
<html lang="tr"><body style="font-family:Arial,sans-serif;color:#1c1c1a;line-height:1.5">
<p>Merhaba,</p>
<p>İngilizce Öğretmenim'e giriş yapmak için aşağıdaki düğmeye bas:</p>
<p><a href="{url}" style="display:inline-block;padding:12px 20px;background:#1c1c1a;color:#ffffff;
text-decoration:none;border-radius:10px">Giriş yap</a></p>
<p style="font-size:13px;color:#6b6b66">Bağlantı {minutes} dakika geçerli ve yalnızca bir kez
kullanılabilir. Bu isteği sen yapmadıysan bu e-postayı yok sayabilirsin.</p>
</body></html>
"""


class EmailSendError(Exception):
    pass


class EmailSender(Protocol):
    def send_login_link(self, email: str, url: str) -> None: ...


def login_message(to: str, url: str) -> EmailMessage:
    minutes = settings.login_token_ttl_minutes
    message = EmailMessage()
    message["Subject"] = SUBJECT
    message["From"] = formataddr((settings.mail_from_name, settings.mail_from))
    message["To"] = to
    message["Message-ID"] = make_msgid(domain=settings.mail_from.split("@")[-1])
    message.set_content(TEXT.format(url=url, minutes=minutes))
    message.add_alternative(HTML.format(url=url, minutes=minutes), subtype="html")
    return message


class ConsoleEmailSender:
    def send_login_link(self, email: str, url: str) -> None:
        log.info("login_link", email=email, url=url)


class SmtpEmailSender:
    def __init__(self, host: str, port: int, user: str | None, password: str | None) -> None:
        self.host, self.port, self.user, self.password = host, port, user, password

    def send_login_link(self, email: str, url: str) -> None:
        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                smtp.starttls()
                if self.user and self.password:
                    smtp.login(self.user, self.password)
                smtp.send_message(login_message(email, url))
        except (smtplib.SMTPException, OSError) as exc:
            # E-posta adresi loga yazılmaz: kişisel veri.
            log.error("login_email_failed", error=type(exc).__name__)
            raise EmailSendError from exc


def sender_from_settings() -> EmailSender:
    if not settings.smtp_host:
        if settings.env != "dev":
            raise RuntimeError("SMTP_HOST tanımlı değil; geliştirme dışında e-posta zorunlu.")
        return ConsoleEmailSender()
    password = settings.smtp_password.get_secret_value() if settings.smtp_password else None
    return SmtpEmailSender(settings.smtp_host, settings.smtp_port, settings.smtp_user, password)
