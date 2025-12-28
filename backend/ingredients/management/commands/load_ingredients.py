import json

from django.core.management.base import BaseCommand

from ingredients.models import Ingredient


class Command(BaseCommand):
    def handle(self, *args, **options):

        with open('ingredients.json', encoding="utf-8") as f:
            ingredients_data = json.load(f)

        for item in ingredients_data:
            _, created = Ingredient.objects.get_or_create(
                name=item["name"],
                measurement_unit=item["measurement_unit"],
            )