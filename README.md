# ![alt text](frontend/src/images/logo-footer.png)

## Кулинарная книга (Foodrgam)  
Проект представляет собой онлайн-сервис для публикации рецептов в виде API приложения.

Функционал сервиса предусматривает:
- регистрацию пользователей и возможность сброса пароля
- создание публикаций с описанием рецепта и списком ингредиентов с их количеством
- добавление своих и чужих рецептов в список избранного
- возможность подписки на других авторов
- добавление рецептов в корзину с возможностью скачивания перечня ингредиентов с общим количеством в формате PDF
- фильтрацию публикаций по тегам
- настраиваемую пагинацию страниц

---
> Ознакомиться с проектом можно здесь:  [Foodgram](https://foodgram.3utilities.com/recipes)  
> Документация API: [ReDoc](https://foodgram.3utilities.com/api/docs/)

## Технологии:
![Python](https://img.shields.io/badge/Python-3.9.13-blue)
![Django](https://img.shields.io/badge/Django-3.2.3-green)
![DjangoRestFramework](https://img.shields.io/badge/DjangoRestFramework-3.12.4-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13.10-green)
![Docker](https://img.shields.io/badge/Docker-24.0.5-blue)

## Особенности реализации
- Развёртывание проекта осуществляется посредством запуска Docker контейнеров — gateway, db, backend и frontend
- Образы для создания и запуска контейнеров запушены на DockerHub
- Запуск проекта осуществляется при помощи workflow c автодеплоем на удаленный сервер
- Реализован функционал для автоматического наполнения БД из CSV файлов при запуске

## Запуск на локальном сервере
- Создайте файл *.env* в корне проекта (шаблон для заполнения файла находится в *.env.example*)
- Установите Docker и Docker Compose (про установку Docker можно почитать в [документации](https://docs.docker.com/engine/install/), про Docker Compose - [здесь](https://docs.docker.com/compose/install/))
- Запустите Docker Compose, выполнив следующую команду
```
docker compose -f docker-compose.yml up --build -d
```
- Скопируйте файлы статики
```
docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
```
```
docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /backend_static/static/
```
- Выполните миграции
```
docker compose -f docker-compose.yml exec backend python manage.py migrate
```
- Создайте суперпользователя
```
docker compose -f docker-compose.yml exec backend python manage.py create_superuser
```
- Заполните БД тестовыми данными
```
docker compose -f docker-compose.yml exec backend python manage.py import_data
```
  
## Авторы
backend: <span style="color: green;">*[Артем Максимов](https://t.me/ovienrait)*</span>

frontend: <span style="color: green;">*[Яндекс Практикум](https://practicum.yandex.ru/)*</span>
