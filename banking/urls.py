from django.urls import path
from . import views

app_name = 'banking'

urlpatterns = [
    path('transfer/', views.halaman_transfer, name='transfer'),
    path('mutasi/', views.halaman_mutasi, name='mutasi'),
    path('topup/', views.halaman_topup, name='topup'),
    path('riwayat-topup/', views.halaman_riwayat_topup, name='riwayat_topup'),
    
    path('antrian-topup/', views.halaman_antrian_setor, name='antrian_topup'),
    path('proses-topup/<int:topup_id>/', views.halaman_proses_setor, name='proses_topup'),
    path('antrian-transfer/', views.halaman_antrian_kirim, name='antrian_transfer'),
    path('proses-transfer/<int:transaksi_id>/', views.halaman_proses_kirim, name='proses_transfer'),
    
    path('laporan/', views.halaman_laporan, name='laporan'),
    path('kelola-rekening/', views.halaman_kelola_rekening, name='kelola_rekening'),
    path('toggle-rekening/<int:rekening_id>/', views.aksi_toggle_rekening,  name='toggle_rekening'),
    
    path('notifikasi/', views.halaman_notifikasi, name='notifikasi'),
]