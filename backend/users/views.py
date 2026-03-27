from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from allauth.account.models import EmailAddress
from allauth.account.internal.flows.email_verification import send_verification_email_for_user

from .models import UserProfile


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    prof, _ = UserProfile.objects.get_or_create(user=request.user)
    email_address = None
    if request.user.email:
        email_address, _ = EmailAddress.objects.get_or_create(
            user=request.user,
            email=request.user.email,
            defaults={"verified": False, "primary": True},
        )
        if not email_address.primary:
            email_address.primary = True
            email_address.save(update_fields=["primary"])

    if request.method == "POST":
        prof.telegram_bot_token = (request.POST.get("telegram_bot_token") or "").strip()
        prof.telegram_default_chat_id = (request.POST.get("telegram_default_chat_id") or "").strip()
        prof.postgres_dsn = (request.POST.get("postgres_dsn") or "").strip()
        prof.save(update_fields=["telegram_bot_token", "telegram_default_chat_id", "postgres_dsn", "updated_at"])
        messages.success(request, "Профиль сохранён")
        return redirect("profile")

    return render(
        request,
        "users/profile.html",
        {
            "profile": prof,
            "email_address": email_address,
        },
    )


@login_required
@require_http_methods(["POST"])
def send_confirmation_email(request):
    if not request.user.email:
        messages.error(request, "У вашего аккаунта не указан email.")
        return redirect("profile")
    email_address, _ = EmailAddress.objects.get_or_create(
        user=request.user,
        email=request.user.email,
        defaults={"verified": False, "primary": True},
    )
    if email_address.verified:
        messages.info(request, "Email уже подтвержден.")
        return redirect("profile")
    sent = send_verification_email_for_user(request, request.user)
    if sent:
        messages.success(request, "Письмо с подтверждением отправлено.")
    else:
        messages.warning(request, "Не удалось отправить письмо подтверждения.")
    return redirect("profile")
