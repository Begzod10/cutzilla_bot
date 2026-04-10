from django.db import models
from django.contrib.auth.models import AbstractUser, Group as AbstractGroup
from apps.common.models import BaseModel
from django.utils.translation import gettext_lazy as _


class Users(AbstractUser, BaseModel):
    first_name = models.CharField(
        verbose_name=_("first name"),
        max_length=150,
        null=True,
        blank=True,
    )
    last_name = models.CharField(
        verbose_name=_("last name"),
        max_length=150,
        null=True,
        blank=True,
    )
    USER = 'user'
    ADMIN = 'admin'
    BARBER = 'barber'
    ROLES = (
        (USER, _('user')),
        (BARBER, _('barber')),
        (ADMIN, _('admin')),
    )
    role = models.CharField(max_length=20, choices=ROLES, default=USER)
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)


