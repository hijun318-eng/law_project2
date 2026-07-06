from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PromptTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.SlugField(max_length=80, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                ("placeholders", models.JSONField(blank=True, default=list)),
                ("current_version", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["key"],
            },
        ),
        migrations.CreateModel(
            name="PromptTemplateVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.PositiveIntegerField()),
                ("content", models.TextField()),
                ("summary", models.CharField(blank=True, max_length=200)),
                ("created_by", models.CharField(default="system", max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("is_current", models.BooleanField(default=False)),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="versions", to="chat.prompttemplate")),
            ],
            options={
                "ordering": ["-version"],
            },
        ),
        migrations.AddConstraint(
            model_name="prompttemplateversion",
            constraint=models.UniqueConstraint(fields=("template", "version"), name="unique_prompt_template_version"),
        ),
    ]
