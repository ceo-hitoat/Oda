from django.db import models

class WeatherData(models.Model):
    eircode = models.CharField(max_length=10)
    latitude = models.FloatField()
    longitude = models.FloatField()
    date = models.DateTimeField()
    temperature_2m = models.FloatField(null=True, blank=True)
    relative_humidity_2m = models.FloatField(null=True, blank=True)
    dew_point_2m = models.FloatField(null=True, blank=True)
    cloud_cover = models.FloatField(null=True, blank=True)
    wind_direction_10m = models.FloatField(null=True, blank=True)
    wind_gusts_10m = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Weather data for {self.eircode} on {self.date}"
