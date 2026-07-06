from django.core.management.base import BaseCommand

from backend.services.prompts import ensure_seed_prompts, list_prompt_templates


class Command(BaseCommand):
    help = "Seed prompt templates from engine/prompts/*.md when they do not exist."

    def handle(self, *args, **options):
        ensure_seed_prompts()
        templates = list_prompt_templates()
        for template in templates:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{template['id']}: v{template['version']}"
                )
            )
