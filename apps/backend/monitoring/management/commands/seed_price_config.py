from django.core.management.base import BaseCommand
from monitoring.models import PriceConfig

DEFAULT_PRICES = [
    {"model_name": "gpt-4o-mini", "prompt_token_price": 0.15, "completion_token_price": 0.60},
    {"model_name": "text-embedding-3-small", "prompt_token_price": 0.02, "completion_token_price": 0.02},
]


class Command(BaseCommand):
    help = "Seed default PriceConfig records"

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0
        for data in DEFAULT_PRICES:
            obj, created = PriceConfig.objects.update_or_create(
                model_name=data["model_name"],
                defaults={
                    "prompt_token_price": data["prompt_token_price"],
                    "completion_token_price": data["completion_token_price"],
                    "updated_by": "system",
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
        self.stdout.write(self.style.SUCCESS(
            f"PriceConfig seeded: {created_count} created, {updated_count} updated"
        ))
