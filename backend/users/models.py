from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from .constants import (
    AVATAR_UPLOAD_TO,
    MAX_LENGTH_EMAIL,
    MAX_LENGTH_NAME,
    MAX_LENGTH_USERNAME,
)


class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        if not username:
            raise ValueError("Username обязателен")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, username, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(
        "email address",
        max_length=MAX_LENGTH_EMAIL,
        unique=True,
        error_messages={
            "unique": "Пользователь с таким email уже существует.",
        },
    )
    first_name = models.CharField("имя", max_length=MAX_LENGTH_NAME)
    last_name = models.CharField("фамилия", max_length=MAX_LENGTH_NAME)
    username = models.CharField(
        "username",
        max_length=MAX_LENGTH_USERNAME,
        unique=True,
        error_messages={
            "unique": "Пользователь с таким username уже существует.",
        },
    )

    avatar = models.ImageField(
        "avatar",
        upload_to=AVATAR_UPLOAD_TO,
        blank=True,
        default="",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["id"]

    def __str__(self):
        return self.email

    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, "url"):
            return self.avatar.url
        return None


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follower",
        verbose_name="Подписчик",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following",
        verbose_name="Автор"
    )
    created = models.DateTimeField("Дата подписки", auto_now_add=True)

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"], name="unique_subscription"
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F("author")),
                name="prevent_self_subscription",
            ),
        ]

    def __str__(self):
        return f"{self.user} подписан на {self.author}"
