"""Outbound email notifications (E30)."""
from opentask.services.email.service import (
    EmailMessage,
    EmailTransport,
    MemoryEmailTransport,
    SmtpEmailTransport,
    email_configured,
    get_email_transport,
    resolve_recipient_email,
    send_notification_email,
    send_test_email,
    set_email_transport,
)

__all__ = [
    "EmailMessage",
    "EmailTransport",
    "MemoryEmailTransport",
    "SmtpEmailTransport",
    "email_configured",
    "get_email_transport",
    "resolve_recipient_email",
    "send_notification_email",
    "send_test_email",
    "set_email_transport",
]
