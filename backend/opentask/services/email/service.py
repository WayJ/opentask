"""SMTP outbound email for inbox notifications (E30)."""
from __future__ import annotations

import asyncio
import logging
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage as StdEmailMessage
from typing import Optional, Protocol

from opentask.config import config

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    to: str
    subject: str
    body: str
    from_addr: Optional[str] = None


class EmailTransport(Protocol):
    def send(self, message: EmailMessage) -> None: ...


@dataclass
class MemoryEmailTransport:
    """In-memory sink for tests."""

    sent: list[EmailMessage] = field(default_factory=list)

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


class SmtpEmailTransport:
    """stdlib smtplib transport."""

    def send(self, message: EmailMessage) -> None:
        from_addr = message.from_addr or config.smtp_from
        host = config.smtp_host
        port = config.smtp_port
        user = config.smtp_user
        password = config.smtp_password
        use_tls = config.smtp_tls

        msg = StdEmailMessage()
        msg["Subject"] = message.subject
        msg["From"] = from_addr
        msg["To"] = message.to
        msg.set_content(message.body or "")

        if use_tls and port != 465:
            with smtplib.SMTP(host, port, timeout=10) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                if user:
                    smtp.login(user, password or "")
                smtp.send_message(msg)
        else:
            # SSL or plain
            factory = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
            with factory(host, port, timeout=10) as smtp:
                if user:
                    smtp.login(user, password or "")
                smtp.send_message(msg)


_transport: Optional[EmailTransport] = None


def set_email_transport(transport: Optional[EmailTransport]) -> None:
    """Override transport (tests). Pass None to restore default."""
    global _transport
    _transport = transport


def get_email_transport() -> EmailTransport:
    if _transport is not None:
        return _transport
    return SmtpEmailTransport()


def email_configured() -> bool:
    """True when SMTP_HOST and SMTP_FROM are set."""
    return bool((config.smtp_host or "").strip() and (config.smtp_from or "").strip())


def resolve_recipient_email(user) -> Optional[str]:
    """user 表无 email 列；username 含 @ 则视为可投递地址。"""
    if user is None:
        return None
    username = getattr(user, "username", None) or ""
    username = str(username).strip()
    if "@" in username and "." in username.split("@")[-1]:
        return username.lower()
    return None


def _deep_link(resource_type: str, resource_id: str) -> Optional[str]:
    base = (config.frontend_base_url or "").rstrip("/")
    if not base or not resource_id:
        return None
    if resource_type == "issue":
        return f"{base}/issue/detail/{resource_id}"
    return f"{base}/{resource_type}/{resource_id}"


def build_notification_email(
    *,
    to: str,
    title: str,
    body: Optional[str],
    notif_type: str,
    resource_type: str,
    resource_id: str,
) -> EmailMessage:
    subject = f"[OpenTask] {title}"[:200]
    lines = [
        title,
        "",
    ]
    if body:
        lines.append(body)
        lines.append("")
    lines.append(f"类型: {notif_type}")
    lines.append(f"资源: {resource_type}/{resource_id}")
    link = _deep_link(resource_type, resource_id)
    if link:
        lines.append("")
        lines.append(f"打开: {link}")
    lines.append("")
    lines.append("— OpenTask 通知（可在设置中关闭邮件）")
    return EmailMessage(to=to, subject=subject, body="\n".join(lines))


async def send_notification_email(
    *,
    to: str,
    title: str,
    body: Optional[str],
    notif_type: str,
    resource_type: str,
    resource_id: str,
) -> bool:
    """Best-effort send; never raises to caller."""
    if not email_configured():
        return False
    msg = build_notification_email(
        to=to,
        title=title,
        body=body,
        notif_type=notif_type,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    try:
        transport = get_email_transport()
        await asyncio.to_thread(transport.send, msg)
        return True
    except Exception:
        logger.exception("email send failed to=%s type=%s", to, notif_type)
        return False


async def send_test_email(*, to: str) -> bool:
    if not email_configured():
        return False
    msg = EmailMessage(
        to=to,
        subject="[OpenTask] 测试邮件",
        body=(
            "这是一封 OpenTask 出站邮件测试信。\n"
            "若你收到此信，说明 SMTP 配置可用。\n\n"
            "— OpenTask"
        ),
    )
    try:
        transport = get_email_transport()
        await asyncio.to_thread(transport.send, msg)
        return True
    except Exception:
        logger.exception("email test send failed to=%s", to)
        raise
