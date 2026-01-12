# Generated manually for Sprint E.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("elections", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="status",
            field=models.CharField(choices=[("INHERIT", "Inherit election window"), ("OPEN", "Open"), ("CLOSED", "Closed")], default="INHERIT", max_length=10),
        ),
        migrations.AddField(
            model_name="post",
            name="start_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="post",
            name="end_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="ElectionArchive",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("note", models.CharField(blank=True, default="", max_length=255)),
                ("data", models.JSONField(default=dict)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("election", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="archives", to="elections.election")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]
