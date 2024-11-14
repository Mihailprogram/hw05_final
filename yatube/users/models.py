from django.contrib.auth.models import AbstractUser

from django.db import models

class CustomUser(AbstractUser):
    profile_picture = models.ImageField('Фото', upload_to='profileimg/', null=True, blank=True)
