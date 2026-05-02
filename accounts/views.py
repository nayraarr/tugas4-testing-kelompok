from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.db.models import Q

from .models import CustomUser
from .forms import EditProfilForm, LoginForm, RegisterNasabahForm, TambahUserForm
from .decorators import supervisor_only
from banking.models import Rekening, Transaksi
from banking.services import buat_rekening_baru


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f'Selamat datang, {user.get_full_name() or user.username}!')
        return redirect('accounts:dashboard')
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'Anda telah berhasil logout.')
    return redirect('accounts:login')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = RegisterNasabahForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        buat_rekening_baru(user) # auto-buat rekening untuk nasabah baru
        login(request, user)
        messages.success(request, 'Registrasi berhasil! Rekening Anda telah dibuat.')
        return redirect('accounts:dashboard')
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def dashboard_view(request):
    user = request.user
    if user.is_nasabah:
        rekening = Rekening.objects.filter(pemilik=user).first()
        transaksi_terakhir = Transaksi.objects.filter(
            Q(rekening_asal=rekening) | Q(rekening_tujuan=rekening)
        ).order_by('-waktu')[:5] if rekening else []
        return render(request, 'accounts/dashboard_nasabah.html', {
            'rekening': rekening,
            'transaksi_terakhir': transaksi_terakhir,
        })
    elif user.is_teller:
        from banking.models import TopUp
        pending_topup = TopUp.objects.filter(status='pending').count()
        pending_transfer = Transaksi.objects.filter(jenis='transfer', status='pending').count()
        return render(request, 'accounts/dashboard_teller.html', {
            'pending_topup': pending_topup,
            'pending_transfer': pending_transfer,
        })
    elif user.is_supervisor:
        from banking.models import TopUp
        total_nasabah = CustomUser.objects.filter(role='nasabah').count()
        total_teller = CustomUser.objects.filter(role='teller').count()
        total_transaksi_hari_ini = Transaksi.objects.filter(
            waktu__date=__import__('datetime').date.today()
        ).count()
        pending_besar = Transaksi.objects.filter(
            jenis='transfer', status='pending', nominal__gte=10_000_000
        ).count()
        return render(request, 'accounts/dashboard_supervisor.html', {
            'total_nasabah': total_nasabah,
            'total_teller': total_teller,
            'total_transaksi_hari_ini': total_transaksi_hari_ini,
            'pending_besar': pending_besar,
        })
    return redirect('accounts:login')

@login_required
def profil_view(request):
    form = EditProfilForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profil berhasil diperbarui.')
        return redirect('accounts:profil')
    return render(request, 'accounts/profil.html', {'form': form})


@login_required
def ganti_password_view(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password berhasil diubah.')
        return redirect('accounts:profil')
    return render(request, 'accounts/ganti_password.html', {'form': form})

@login_required
@supervisor_only
def kelola_user_view(request):
    q = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    users = CustomUser.objects.exclude(is_superuser=True)
    if q:
        users = users.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    if role_filter:
        users = users.filter(role=role_filter)
    return render(request, 'accounts/kelola_user.html', {'users': users, 'q': q, 'role_filter': role_filter})


@login_required
@supervisor_only
def tambah_user_view(request):
    form = TambahUserForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        if user.role == 'nasabah':
            from banking.services import buat_rekening_baru
            buat_rekening_baru(user)
        messages.success(request, f'User {user.username} berhasil ditambahkan.')
        return redirect('accounts:kelola_user')
    return render(request, 'accounts/tambah_user.html', {'form': form})


@login_required
@supervisor_only
def toggle_aktif_user_view(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(CustomUser, pk=user_id)
        if user != request.user:
            user.is_active = not user.is_active
            user.save()
            status = 'diaktifkan' if user.is_active else 'dinonaktifkan'
            messages.success(request, f'User {user.username} berhasil {status}.')
    return redirect('accounts:kelola_user')