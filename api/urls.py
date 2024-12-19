from django.urls import path
from . views import CoordinatesReturnView, AnalyticsView, EircodeWeatherView

urlpatterns = [
    path('environmental_analytics/coordinates/', CoordinatesReturnView.as_view(), name='eircode'),
    path('environmental_analytics/analytics/', AnalyticsView.as_view(), name='analytics'),
    path('environmental_analytics/eircode_weather/', EircodeWeatherView.as_view(), name='eircode_weather'),
]
