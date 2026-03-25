from __future__ import annotations

from allauth.account.forms import LoginForm, SignupForm


class EmailPasswordLoginForm(LoginForm):
    """Вход: email + пароль."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["login"].label = "Электронная почта"
        self.fields["password"].label = "Пароль"
        if "remember" in self.fields:
            self.fields["remember"].label = "Запомнить меня"


class EmailPasswordSignupForm(SignupForm):
    """Регистрация: email + пароль + подтверждение пароля."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if "email" in self.fields:
            self.fields["email"].label = "Электронная почта"
        if "password1" in self.fields:
            self.fields["password1"].label = "Пароль"
        if "password2" in self.fields:
            self.fields["password2"].label = "Пароль ещё раз"
