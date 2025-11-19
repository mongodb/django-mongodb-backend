from django.contrib.gis.db import models


class NamedModel(models.Model):
    name = models.CharField(max_length=30)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class City(NamedModel):
    point = models.PointField()


class MultiFields(NamedModel):
    city = models.ForeignKey(City, models.CASCADE)
    point = models.PointField()
    poly = models.PolygonField()


class Zipcode(models.Model):
    code = models.CharField(max_length=10)
    poly = models.PolygonField(geography=True)
