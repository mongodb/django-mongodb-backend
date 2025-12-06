from django.contrib.gis.db import models


class City(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField()

    def __str__(self):
        return self.name


class Zipcode(models.Model):
    code = models.CharField(max_length=10)
    poly = models.PolygonField(geography=True)
