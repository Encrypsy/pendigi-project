import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pendigi.settings")
django.setup()

from django.core import serializers
from django.apps import apps


exclude_models = {
    "contenttypes.contenttype",
    "auth.permission",
    "admin.logentry",
    "sessions.session",
}

objects = []

for model in apps.get_models():
    label = f"{model._meta.app_label}.{model._meta.model_name}"

    if label in exclude_models:
        continue

    print(f"Exporting {label}...")

    for obj in model.objects.all():
        objects.append(obj)

with open("data_utf8.json", "w", encoding="utf-8") as f:
    serializers.serialize(
        "json",
        objects,
        stream=f,
        use_natural_foreign_keys=True,
        use_natural_primary_keys=True,
    )

print(f"\nSUCCESS: {len(objects)} objects exported.")