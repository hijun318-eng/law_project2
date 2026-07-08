from django import forms
from django.contrib.auth.models import User

from monitoring.models import PriceConfig

_REQUIRED_MESSAGE = "모든 항목을 입력해주세요."


class RegisterForm(forms.Form):
    """회원가입 폼. register_view가 직접 하던 필수값/중복이메일/비밀번호 확인 검증을
    Django Forms로 옮겨 필드별 clean 메서드로 표현한다."""

    name = forms.CharField(
        max_length=150,
        error_messages={"required": _REQUIRED_MESSAGE},
    )
    email = forms.EmailField(
        error_messages={"required": _REQUIRED_MESSAGE, "invalid": _REQUIRED_MESSAGE},
    )
    password = forms.CharField(
        min_length=8,
        error_messages={
            "required": _REQUIRED_MESSAGE,
            "min_length": "비밀번호는 8자 이상이어야 합니다.",
        },
    )
    password_confirm = forms.CharField(
        error_messages={"required": _REQUIRED_MESSAGE},
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("이미 가입된 이메일이 있습니다.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("비밀번호가 일치하지 않습니다.")
        return cleaned_data


class PriceConfigForm(forms.ModelForm):
    """관리자 콘솔의 토큰당 가격 설정 생성/수정 폼.
    model_name으로 기존 레코드를 찾아 instance로 넘기면 update_or_create와
    동일하게 동작(신규면 생성, 기존이면 수정)한다."""

    prompt_token_price = forms.FloatField(
        error_messages={"required": "Prices must be numbers", "invalid": "Prices must be numbers"},
    )
    completion_token_price = forms.FloatField(
        error_messages={"required": "Prices must be numbers", "invalid": "Prices must be numbers"},
    )

    class Meta:
        model = PriceConfig
        fields = ["model_name", "prompt_token_price", "completion_token_price"]
        error_messages = {
            "model_name": {"required": "model_name is required"},
        }

    def clean_model_name(self):
        model_name = self.cleaned_data["model_name"].strip()
        if not model_name:
            raise forms.ValidationError("model_name is required")
        return model_name

    def clean_prompt_token_price(self):
        value = self.cleaned_data["prompt_token_price"]
        if value < 0:
            raise forms.ValidationError("Prices cannot be negative")
        return value

    def clean_completion_token_price(self):
        value = self.cleaned_data["completion_token_price"]
        if value < 0:
            raise forms.ValidationError("Prices cannot be negative")
        return value


def first_error_message(form: forms.BaseForm) -> str:
    """폼 에러 중 하나를 골라 기존 API가 쓰던 단일 문자열 에러 메시지 형태로 변환."""
    non_field = form.non_field_errors()
    if non_field:
        return non_field[0]
    for field in form.fields:
        if field in form.errors:
            return form.errors[field][0]
    return "입력값을 확인해주세요."
