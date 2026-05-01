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
        # buat_rekening_baru(user) # auto-buat rekening untuk nasabah baru
        login(request, user)
        messages.success(request, 'Registrasi berhasil! Rekening Anda telah dibuat.')
        return redirect('accounts:dashboard')
    return render(request, 'accounts/register.html', {'form': form})
