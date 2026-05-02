from django.urls import path
from . import views

app_name = 'banking'

urlpatterns = [
    path('transfer/', views.transfer_view, name='transfer'),
    path('mutasi/', views.mutasi_view, name='mutasi'),
    path('topup/', views.topup_view, name='topup'),
    path('riwayat-topup/', views.riwayat_topup_view, name='riwayat_topup'),
    
    path('antrian-topup/', views.antrian_topup_view, name='antrian_topup'),
    path('proses-topup/<int:topup_id>/', views.proses_topup_view, name='proses_topup'),
    path('antrian-transfer/', views.antrian_transfer_view, name='antrian_transfer'),
    path('proses-transfer/<int:transaksi_id>/', views.proses_transfer_view, name='proses_transfer'),
    
    path('laporan/', views.laporan_view, name='laporan'),
    path('kelola-rekening/', views.kelola_rekening_view, name='kelola_rekening'),
    path('toggle-rekening/<int:rekening_id>/', views.toggle_rekening_view,  name='toggle_rekening'),
    
    path('notifikasi/', views.notifikasi_view, name='notifikasi'),
]