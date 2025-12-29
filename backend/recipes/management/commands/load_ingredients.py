import json

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = "Загружает ингредиенты из JSON файла в БД"

    def handle(self, *args, **options):

        self.stdout.write(f"Загрузка ингредиентов из ingredients.json")

        with open("ingredients.json", encoding="utf-8") as f:
            ingredients_data = json.load(f)

        for item in ingredients_data:
            _, created = Ingredient.objects.get_or_create(
                name=item["name"],
                measurement_unit=item["measurement_unit"],
            )
