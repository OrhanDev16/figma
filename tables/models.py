from django.db import models


class Table(models.Model):
    title = models.CharField(max_length=100)
