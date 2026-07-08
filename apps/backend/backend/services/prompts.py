import re
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from chat.models import PromptTemplate, PromptTemplateVersion


PROMPT_DIR = Path(__file__).resolve().parents[2] / "engine" / "prompts"

PROMPT_SEEDS = [
    {
        "key": "answer_prompt",
        "filename": "answer_prompt.md",
        "name": "answer_prompt",
        "description": "AI 상담 답변 생성 프롬프트",
    },
    {
        "key": "procedure_prompt",
        "filename": "procedure_prompt.md",
        "name": "procedure_prompt",
        "description": "절차 안내 생성 프롬프트",
    },
    {
        "key": "calculator_prompt",
        "filename": "calculator_prompt.md",
        "name": "calculator_prompt",
        "description": "수당/퇴직금 계산 에이전트 프롬프트",
    },
    {
        "key": "news_prompt",
        "filename": "news_prompt.md",
        "name": "news_prompt",
        "description": "노동 뉴스 검색 에이전트 프롬프트",
    },
    {
        "key": "precedent_summary_prompt",
        "filename": "precedent_summary_prompt.md",
        "name": "precedent_summary_prompt",
        "description": "판례 요약/SAC 생성 프롬프트",
    },
]


def _extract_placeholders(content: str) -> list[str]:
    tokens = set(re.findall(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", content))
    tokens.update(re.findall(r"\$[a-zA-Z_][a-zA-Z0-9_]*", content))
    return sorted(tokens)


def _read_seed(filename: str) -> str:
    path = PROMPT_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def ensure_seed_prompts() -> None:
    for seed in PROMPT_SEEDS:
        if PromptTemplate.objects.filter(key=seed["key"]).exists():
            continue

        content = _read_seed(seed["filename"])
        template = PromptTemplate.objects.create(
            key=seed["key"],
            name=seed["name"],
            description=seed["description"],
            placeholders=_extract_placeholders(content),
            current_version=1,
        )
        PromptTemplateVersion.objects.create(
            template=template,
            version=1,
            content=content,
            summary="파일에서 최초 등록",
            created_by="system",
            is_current=True,
        )


def _format_dt(value) -> str:
    if not value:
        return ""
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M")


def _version_to_dict(version: PromptTemplateVersion) -> dict:
    return {
        "version": version.version,
        "updated_at": _format_dt(version.created_at),
        "updated_by": version.created_by,
        "summary": version.summary or "내용 업데이트",
        "content": version.content,
    }


def _template_to_dict(template: PromptTemplate, include_content: bool = True) -> dict:
    current = template.versions.filter(is_current=True).first()
    if current is None:
        current = template.versions.order_by("-version").first()

    data = {
        "id": template.key,
        "name": template.name,
        "description": template.description,
        "version": template.current_version,
        "placeholders": template.placeholders,
        "updated_at": _format_dt(current.created_at if current else template.updated_at),
        "updated_by": current.created_by if current else "system",
        "history": [_version_to_dict(v) for v in template.versions.all()],
    }
    if include_content:
        data["content"] = current.content if current else ""
    return data


def list_prompt_templates() -> list[dict]:
    ensure_seed_prompts()
    templates = PromptTemplate.objects.filter(is_active=True).prefetch_related("versions")
    return [_template_to_dict(t, include_content=True) for t in templates]


def get_prompt_template(template_id: str) -> dict:
    ensure_seed_prompts()
    template = (
        PromptTemplate.objects
        .filter(key=template_id, is_active=True)
        .prefetch_related("versions")
        .first()
    )
    return _template_to_dict(template) if template else {}


def validate_prompt_content(template_id: str, content: str) -> list[str]:
    ensure_seed_prompts()
    template = PromptTemplate.objects.filter(key=template_id, is_active=True).first()
    if not template:
        return ["프롬프트 템플릿을 찾을 수 없습니다."]
    if not content.strip():
        return ["프롬프트 내용은 비워둘 수 없습니다."]
    return [
        f"필수 플레이스홀더 {p} 가 누락되었습니다."
        for p in template.placeholders
        if p not in content
    ]


@transaction.atomic
def save_prompt_template(template_id: str, content: str, updated_by: str = "관리자") -> None:
    ensure_seed_prompts()
    # 클라이언트가 "validate"를 건너뛰고 바로 "save"를 호출해도 필수 플레이스홀더
    # 누락 등 검증 없이 저장되지 않도록 서버에서도 동일한 검증을 강제한다.
    errors = validate_prompt_content(template_id, content)
    if errors:
        raise ValidationError("; ".join(errors))

    template = PromptTemplate.objects.select_for_update().get(key=template_id, is_active=True)
    new_version = template.current_version + 1

    template.versions.update(is_current=False)
    PromptTemplateVersion.objects.create(
        template=template,
        version=new_version,
        content=content,
        summary="내용 업데이트",
        created_by=updated_by,
        is_current=True,
    )
    template.current_version = new_version
    template.save(update_fields=["current_version", "updated_at"])


@transaction.atomic
def rollback_prompt_template(template_id: str, version, updated_by: str = "관리자") -> None:
    ensure_seed_prompts()
    template = PromptTemplate.objects.select_for_update().get(key=template_id, is_active=True)
    target = template.versions.get(version=int(version))
    new_version = template.current_version + 1

    template.versions.update(is_current=False)
    PromptTemplateVersion.objects.create(
        template=template,
        version=new_version,
        content=target.content,
        summary=f"v{target.version}으로 롤백",
        created_by=updated_by,
        is_current=True,
    )
    template.current_version = new_version
    template.save(update_fields=["current_version", "updated_at"])


def load_active_prompt(key: str, fallback_filename: str | None = None) -> str:
    try:
        ensure_seed_prompts()
        template = PromptTemplate.objects.filter(key=key, is_active=True).first()
        if template:
            current = template.versions.filter(is_current=True).first()
            if current:
                return current.content
    except Exception:
        pass

    filename = fallback_filename or f"{key}.md"
    return _read_seed(filename)
