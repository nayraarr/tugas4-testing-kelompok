from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages

from .forms import LoginForm

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
