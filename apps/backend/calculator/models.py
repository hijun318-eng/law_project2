from django.db import models


class CalculatorHistory(models.Model):
    CALC_TYPE_CHOICES = [
        ('retirement', '퇴직금'),
        ('severance', '해고예고수당'),
        ('annual', '연차수당'),
        ('severance_pay', '퇴직금'),
        ('weekly', '주휴수당'),
        ('overtime', '야근수당'),
        ('other', '기타 계산'),
    ]

    calc_type = models.CharField(max_length=20, choices=CALC_TYPE_CHOICES, default='other')
    input_data = models.JSONField(default=dict)
    result_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'calculator_history'

    def __str__(self):
        return f"[{self.calc_type}] {self.created_at}"
