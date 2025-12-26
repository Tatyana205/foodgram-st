#!/bin/bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
cp -r static /static/
gunicorn config.wsgi:application --bind 0.0.0.0:8000