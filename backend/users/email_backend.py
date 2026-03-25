from __future__ import annotations

from django.core.mail.backends.smtp import EmailBackend

from .models import EmailSendLog


class LoggingSMTPEmailBackend(EmailBackend):
    """
    SMTP backend that logs send status to DB (Django admin).
    """

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        logs = [
            EmailSendLog(
                subject=(m.subject or "")[:998],
                from_email=m.from_email or "",
                to_emails=list(m.to or []),
                status="queued",
            )
            for m in email_messages
        ]
        EmailSendLog.objects.bulk_create(logs)

        try:
            sent = super().send_messages(email_messages)
        except Exception as e:  # noqa: BLE001
            EmailSendLog.objects.filter(id__in=[l.id for l in logs]).update(
                status="failed",
                error=str(e),
            )
            raise

        # Django SMTP backend returns number of emails sent successfully
        # We can’t perfectly map partial failures per-message without deeper hooks.
        new_status = "sent" if sent == len(logs) else "partial"
        EmailSendLog.objects.filter(id__in=[l.id for l in logs]).update(status=new_status)
        return sent

