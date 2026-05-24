import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache

from .permission import khusus_supervisor
from .models import CustomUser
from .forms import EditProfilForm, LoginForm, RegisterNasabahForm, TambahUserForm
from banking.models import Rekening, Transaksi, TopUp
from banking.services import buat_rekening_baru

# QUERY BUILDER
def _bangun_filter_pengguna(params: dict) -> QuerySet:
    qs = CustomUser.objects.exclude(is_superuser=True)

    kata_kunci = params.get('q', '').strip()
    if kata_kunci:
        qs = qs.filter(
            Q(username__icontains=kata_kunci)
            | Q(first_name__icontains=kata_kunci)
            | Q(last_name__icontains=kata_kunci)
        )

    peran = params.get('role', '').strip()
    if peran:
        qs = qs.filter(role=peran)

    return qs

# RENDER HELPERS
def _render_dasbor_nasabah(request):
    rekening = Rekening.objects.filter(pemilik=request.user).first()
    if rekening:
        transaksi_terakhir = (
            Transaksi.objects
            .filter(Q(rekening_asal=rekening) | Q(rekening_tujuan=rekening))
            .order_by('-waktu')[:5]
        )
    else:
        transaksi_terakhir = []
    return render(request, 'accounts/dashboard_nasabah.html', {
        'rekening': rekening,
        'transaksi_terakhir': transaksi_terakhir,
    })


def _render_dasbor_teller(request):
    konteks = {
        'pending_topup': TopUp.objects.filter(status='pending').count(),
        'pending_transfer': Transaksi.objects.filter(jenis='transfer', status='pending').count(),
    }
    return render(request, 'accounts/dashboard_teller.html', konteks)


def _render_dasbor_supervisor(request):
    konteks = {
        'total_nasabah': CustomUser.objects.filter(role='nasabah').count(),
        'total_teller': CustomUser.objects.filter(role='teller').count(),
        'total_transaksi_hari_ini': Transaksi.objects.filter(
            waktu__date=datetime.date.today()
        ).count(),
        'pending_besar': Transaksi.objects.filter(
            jenis='transfer', status='pending', nominal__gte=10_000_000
        ).count(),
    }
    return render(request, 'accounts/dashboard_supervisor.html', konteks)

_PETA_RENDERER = {
    'nasabah':    _render_dasbor_nasabah,
    'teller':     _render_dasbor_teller,
    'supervisor': _render_dasbor_supervisor,
}

# HELPER FUNCTIONS
def _proses_login(request, form) -> bool:
    if not form.is_valid():
        return False
    pengguna = form.get_user()
    login(request, pengguna)
    nama = pengguna.get_full_name() or pengguna.username
    messages.success(request, f'Selamat datang, {nama}!')
    return True

def _proses_registrasi(request, form) -> bool:
    if not form.is_valid():
        return False
    pengguna = form.save()
    buat_rekening_baru(pengguna)
    login(request, pengguna, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, 'Registrasi berhasil! Rekening Anda telah dibuat.')
    return True


def _proses_tambah_user(request, form) -> bool:
    if not form.is_valid():
        return False
    pengguna = form.save()
    if pengguna.role == 'nasabah':
        buat_rekening_baru(pengguna)
    messages.success(request, f'User {pengguna.username} berhasil ditambahkan.')
    return True


def _eksekusi_toggle_user(aktor, target_id: int):
    target = get_object_or_404(CustomUser, pk=target_id)
    if target == aktor:
        return None
    target.is_active = not target.is_active
    target.save()
    status_label = 'diaktifkan' if target.is_active else 'dinonaktifkan'
    return f'User {target.username} berhasil {status_label}.'


# VIEWS FUNCTIONS
@csrf_protect
def halaman_login(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and _proses_login(request, form):
        return redirect('accounts:dashboard')
    return render(request, 'accounts/login.html', {'form': form})

@csrf_protect
def halaman_logout(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'Anda telah berhasil logout.')
    return redirect('accounts:login')

@csrf_protect
def halaman_registrasi(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = RegisterNasabahForm(request.POST or None)
    if request.method == 'POST' and _proses_registrasi(request, form):
        return redirect('accounts:dashboard')
    return render(request, 'accounts/register.html', {'form': form})

@never_cache
@login_required
def halaman_beranda(request):
    """Dispatch ke renderer yang sesuai berdasarkan peran pengguna."""
    peran = request.user.role
    renderer = _PETA_RENDERER.get(peran)
    if renderer is None:
        return redirect('accounts:login')
    return renderer(request)

@never_cache
@login_required(login_url='/login/')
@csrf_protect
def halaman_profil(request):
    form = EditProfilForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profil berhasil diperbarui.')
        return redirect('accounts:profil')
    return render(request, 'accounts/profil.html', {'form': form})

@login_required(login_url='/login/')
@csrf_protect
def halaman_ganti_sandi(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        pengguna = form.save()
        update_session_auth_hash(request, pengguna)
        messages.success(request, 'Password berhasil diubah.')
        return redirect('accounts:profil')
    return render(request, 'accounts/ganti_password.html', {'form': form})


@login_required
@khusus_supervisor
def halaman_kelola_pengguna(request):
    daftar_user = _bangun_filter_pengguna(request.GET)
    return render(request, 'accounts/kelola_user.html', {
        'users': daftar_user,
        'q': request.GET.get('q', ''),
        'role_filter': request.GET.get('role', ''),
    })


@login_required
@csrf_protect
@khusus_supervisor
def halaman_tambah_pengguna(request):
    form = TambahUserForm(request.POST or None)
    if request.method == 'POST' and _proses_tambah_user(request, form):
        return redirect('accounts:kelola_user')
    return render(request, 'accounts/tambah_user.html', {'form': form})

@login_required
@csrf_protect
@khusus_supervisor
def aksi_toggle_pengguna(request, user_id):
    if request.method == 'POST':
        pesan = _eksekusi_toggle_user(request.user, user_id)
        if pesan:
            messages.success(request, pesan)
    return redirect('accounts:kelola_user')
