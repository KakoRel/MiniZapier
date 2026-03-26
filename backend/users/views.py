from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .models import UserProfile


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    prof, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        prof.telegram_bot_token = (request.POST.get("telegram_bot_token") or "").strip()
        prof.telegram_default_chat_id = (request.POST.get("telegram_default_chat_id") or "").strip()
        prof.save(update_fields=["telegram_bot_token", "telegram_default_chat_id", "updated_at"])
        messages.success(request, "Профиль сохранён")
        return redirect("profile")

    return render(request, "users/profile.html", {"profile": prof})
