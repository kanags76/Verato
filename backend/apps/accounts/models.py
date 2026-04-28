from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    organisation = models.ForeignKey(
        'Organisation',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='users',
    )

    class Meta:
        db_table = 'accounts_user'


class Organisation(models.Model):
    name       = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'accounts_organisation'
