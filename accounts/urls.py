from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profil/', views.profil_view, name='profil'),
    path('ganti-password/', views.ganti_password_view, name='ganti_password'),
    
    path('kelola-user/', views.kelola_user_view, name='kelola_user'),
    path('tambah-user/', views.tambah_user_view, name='tambah_user'),
    path('toggle-aktif/<int:user_id>/', views.toggle_aktif_user_view, name='toggle_aktif'),
]