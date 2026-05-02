from django.urls import path
from . import views

app_name = 'banking'

urlpatterns = [
    path('transfer/', views.transfer_view, name='transfer'),
    path('mutasi/', views.mutasi_view, name='mutasi'),
    path('topup/', views.topup_view, name='topup'),
    path('riwayat-topup/', views.riwayat_topup_view, name='riwayat_topup'),
]