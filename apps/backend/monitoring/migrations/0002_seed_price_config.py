from django.db import migrations

DEFAULT_PRICES = [
    {"model_name": "gpt-4o-mini", "prompt_token_price": 0.15, "completion_token_price": 0.60},
    {"model_name": "gpt-5.4-nano", "prompt_token_price": 0.20, "completion_token_price": 1.25},
    {"model_name": "text-embedding-3-small", "prompt_token_price": 0.02, "completion_token_price": 0.02},
]


def seed_price_config(apps, schema_editor):
    PriceConfig = apps.get_model("monitoring", "PriceConfig")
    for data in DEFAULT_PRICES:
        PriceConfig.objects.update_or_create(
            model_name=data["model_name"],
            defaults={
                "prompt_token_price": data["prompt_token_price"],
                "completion_token_price": data["completion_token_price"],
                "updated_by": "system",
            },
        )


def unseed_price_config(apps, schema_editor):
    PriceConfig = apps.get_model("monitoring", "PriceConfig")
    PriceConfig.objects.filter(
        model_name__in=[d["model_name"] for d in DEFAULT_PRICES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("monitoring", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_price_config, unseed_price_config),
    ]
