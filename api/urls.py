from django.urls import path
from . views import CoordinatesReturnView, AnalyticsView

urlpatterns = [
    path('environmental_analytics/coordinates/', CoordinatesReturnView.as_view(), name='eircode'),
    path('environmental_analytics/analytics/', AnalyticsView.as_view(), name='analytics'),
]
