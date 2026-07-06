from django.db import models
from django.contrib.auth.models import User


class ChatHistory(models.Model):
    MODE_CHOICES = [
        ('rag', 'RAG 질의응답'),
        ('calculator', '법률 계산기'),
        ('news', '판례/법률 뉴스'),
        ('supervisor', '전문 상담사'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=255, db_index=True)
    question = models.TextField()
    answer = models.TextField()
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='rag')
    sources = models.JSONField(default=list, blank=True)
    category = models.CharField(max_length=50, blank=True, default="")
    feedback = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'chat_history'

    def __str__(self):
        return f"[{self.mode}] {self.question[:50]}"


class PromptTemplate(models.Model):
    key = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    placeholders = models.JSONField(default=list, blank=True)
    current_version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return f"{self.key} v{self.current_version}"


class PromptTemplateVersion(models.Model):
    template = models.ForeignKey(
        PromptTemplate,
        related_name="versions",
        on_delete=models.CASCADE,
    )
    version = models.PositiveIntegerField()
    content = models.TextField()
    summary = models.CharField(max_length=200, blank=True)
    created_by = models.CharField(max_length=120, default="system")
    created_at = models.DateTimeField(auto_now_add=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "version"],
                name="unique_prompt_template_version",
            ),
        ]

    def __str__(self):
        return f"{self.template.key} v{self.version}"
