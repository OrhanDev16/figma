from django.db import models

# Create your models here.


class Table(models.Model):
    title = models.CharField(max_length=100)