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
    feedback = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'chat_history'

    def __str__(self):
        return f"[{self.mode}] {self.question[:50]}"
