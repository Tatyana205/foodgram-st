### Описание.
Данный проект является это полноценным веб-приложением для публикации, поиска и обмена кулинарными рецептами. У пользователей есть возможность создавать свой список рецептов, подписываться на других авторов и формировать список покупок для выбранных блюд.

### Установка. Как запустить проект:

#### Запуск на проде

Перейти в папку ./infra

Скачать файл

```
docker-compose.prod.yml
```

Создать в той же дирректории файл .env

Ввести и запустить команду

```
docker compose -f docker-compose.prod.yml up
```

#### Запуск локально

Скачать весь проект

Перейти в папку ./infra

Создать в той же дирректории файл .env

Ввести и запустить команду

```
docker compose -f docker-compose.yml up --build
```

Проект откроется на

```
http://localhost
```

API откроестя на

```
http://localhost/api
```

Доки откроются на
```
http://localhost/api/docs
```

Админ-зона откроестя на

```
http://localhost/admin
```

#### Создание суперпользователя

```
docker compose -f <имя compose файла> exec backend python manage.py createsuperuser
```

#### Загрузка ингридиентов

```
docker compose -f <имя compose файла> exec backend python manage.py load_ingredients
```