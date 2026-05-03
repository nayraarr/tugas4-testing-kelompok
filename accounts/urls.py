from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.halaman_login, name='login'),
    path('logout/', views.halaman_logout, name='logout'),
    path('register/', views.halaman_registrasi, name='register'),
    
    path('dashboard/', views.halaman_beranda, name='dashboard'),
    path('profil/', views.halaman_profil, name='profil'),
    path('ganti-password/', views.halaman_ganti_sandi, name='ganti_password'),
    
    path('kelola-user/', views.halaman_kelola_pengguna, name='kelola_user'),
    path('tambah-user/', views.halaman_tambah_pengguna, name='tambah_user'),
    path('toggle-aktif/<int:user_id>/', views.aksi_toggle_pengguna, name='toggle_aktif_user'),
]