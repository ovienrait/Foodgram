from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Модель для пользователей"""

    email = models.EmailField('почта', max_length=254, unique=True)
    avatar = models.ImageField(
        upload_to='users/images/', blank=True, null=True, default=None)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        ordering = ('username',)
        verbose_name = 'пользователя'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Subscription(models.Model):
    """Модель для подписок"""

    subscriber = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='пользователь',
        related_name='subscriber')
    subscription = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='подписан на пользователя',
        related_name='subscription')

    class Meta:
        verbose_name = 'подписку'
        verbose_name_plural = 'Подписки'
        constraints = [models.UniqueConstraint(
            fields=['subscriber', 'subscription'],
            name='unique_subscriber_subscription')]
