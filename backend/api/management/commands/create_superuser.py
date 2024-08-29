from django.core.management.base import BaseCommand

from users.models import CustomUser


class Command(BaseCommand):
    """Команда для создания суперпользователя"""

    def handle(self, *args, **options):
        if not CustomUser.objects.filter(is_superuser=True).exists():
            CustomUser.objects.create_superuser(
                username='admin', email='admin@example.com',
                password='password')
            self.stdout.write(
                self.style.SUCCESS('Создан суперпользователь "admin"'))
        else:
            self.stdout.write(
                self.style.SUCCESS('Суперпользователь уже существует'))
