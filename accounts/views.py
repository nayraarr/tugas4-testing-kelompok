from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.db.models import Q

from .models import CustomUser
from .forms import LoginForm, RegisterNasabahForm
from .decorators import supervisor_only
# from banking.models import Rekening, Transaksi
# from banking.services import buat_rekening_baru


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        if user:
            login(request, user)
            messages.success(request, f'Selamat datang, {user.get_full_name() or user.username}!')
            return redirect('accounts:dashboard')
    return render(request, 'accounts/login.html', {'form': form})

@login_required
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
        # buat_rekening_baru(user) # auto-buat rekening untuk nasabah baru
        login(request, user)
        messages.success(request, 'Registrasi berhasil! Rekening Anda telah dibuat.')
        return redirect('accounts:dashboard')
    return render(request, 'accounts/register.html', {'form': form})


@login_required(login_url='/login/')
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


@login_required(login_url='/login/')
def profil_view(request):
    form = EditProfilForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profil berhasil diperbarui.')
        return redirect('accounts:profil')
    return render(request, 'accounts/profil.html', {'form': form})


@login_required(login_url='/login/')
def ganti_password_view(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password berhasil diubah.')
        return redirect('accounts:profil')
    return render(request, 'accounts/ganti_password.html', {'form': form})
