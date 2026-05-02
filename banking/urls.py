from django.urls import path
from . import views

app_name = 'banking'

urlpatterns = [
    path('transfer/', views.transfer_view, name='transfer'),
    path('mutasi/', views.mutasi_view, name='mutasi'),
]