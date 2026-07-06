from django.contrib import admin

from monitoring.models import NodeExecutionLog, LLMUsageLog, PriceConfig

admin.site.register(NodeExecutionLog)
admin.site.register(LLMUsageLog)
admin.site.register(PriceConfig)
