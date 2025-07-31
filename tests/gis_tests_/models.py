from django.contrib.gis.db import models


class City(models.Model):
    point = models.PointField()
