from django.db import models


class NodeExecutionLog(models.Model):
    id = models.AutoField(primary_key=True)
    session_id = models.CharField(max_length=255, db_index=True)
    node_name = models.CharField(max_length=100)
    elapsed_ms = models.FloatField()
    status = models.CharField(max_length=100, default='success')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'monitoring_nodeexecutionlog'


class LLMUsageLog(models.Model):
    id = models.AutoField(primary_key=True)
    session_id = models.CharField(max_length=255, db_index=True)
    node_name = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    call_type = models.CharField(max_length=20, default='llm')
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'monitoring_llmusagelog'


class PriceConfig(models.Model):
    id = models.AutoField(primary_key=True)
    model_name = models.CharField(max_length=100, unique=True)
    prompt_token_price = models.FloatField()
    completion_token_price = models.FloatField()
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=120, default='system')

    class Meta:
        db_table = 'monitoring_priceconfig'

    def __str__(self):
        return f"{self.model_name}: input=${self.prompt_token_price}/1M, output=${self.completion_token_price}/1M"
