import bleach
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, QuerySet
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect

from accounts.decorators import nasabah_only, staff_only, supervisor_only
from accounts.permission import khusus_nasabah, khusus_staf, khusus_supervisor
from banking import operasi
from banking.forms import ApprovalForm, MutasiFilterForm, TransferForm, TopUpForm
from banking.models import Notifikasi, Rekening, TopUp, Transaksi

from decimal import Decimal, InvalidOperation  
from django.db import transaction, connection
from django.http import HttpResponseBadRequest
from django.views.decorators.cache import never_cache

class QueryRiwayat:
    def __init__(self, rekening: Rekening):
        self._qs: QuerySet = Transaksi.objects.filter(
            Q(rekening_asal=rekening) | Q(rekening_tujuan=rekening)
        )
        self._rekening = rekening

    def filter_rentang(self, periode: str = '30') -> 'QueryRiwayat':
        if periode and periode != 'all':
            batas = timezone.now() - timedelta(days=int(periode))
            self._qs = self._qs.filter(waktu__gte=batas)
        return self

    def filter_jenis(self, jenis: str = '') -> 'QueryRiwayat':
        if jenis:
            self._qs = self._qs.filter(jenis=jenis)
        return self

    def urutkan(self, kolom: str = '-waktu') -> 'QueryRiwayat':
        self._qs = self._qs.order_by(kolom)
        return self

    def hasil(self) -> QuerySet:
        return self._qs

    def ringkasan_nominal(self) -> dict:
        masuk  = self._qs.filter(rekening_tujuan=self._rekening, status='approved') \
                         .aggregate(t=Sum('nominal'))['t'] or 0
        keluar = self._qs.filter(rekening_asal=self._rekening, status='approved') \
                         .aggregate(t=Sum('nominal'))['t'] or 0
        return {'total_masuk': masuk, 'total_keluar': keluar}


def _query_antrian_setor(petugas) -> tuple[QuerySet, QuerySet]:
    pending  = TopUp.objects.filter(status='pending') \
                            .select_related('rekening__pemilik')
    selesai  = TopUp.objects.exclude(status='pending') \
                            .select_related('rekening__pemilik', 'diproses_oleh')[:20]
    return pending, selesai


def _query_antrian_kirim(petugas) -> tuple[QuerySet, QuerySet]:
    base = Transaksi.objects.filter(jenis='transfer', status='pending') \
                            .select_related('rekening_asal__pemilik', 'rekening_tujuan__pemilik')

    pending = base.filter(nominal__lt=10_000_000) if petugas.is_teller else base

    selesai = (
        Transaksi.objects
        .filter(jenis='transfer')
        .exclude(status='pending')
        .select_related('rekening_asal__pemilik', 'rekening_tujuan__pemilik', 'diproses_oleh')[:20]
    )
    return pending, selesai

def _bangun_queryset_laporan(params: dict) -> tuple[QuerySet, QuerySet]:
    """Bangun queryset transaksi & topup berdasarkan filter periode + teller."""
    periode       = params.get('periode', '30')
    teller_filter = params.get('teller', '')

    qs_transfer = Transaksi.objects.filter(status='approved')
    qs_topup    = TopUp.objects.filter(status='selesai')

    if periode != 'all':
        batas = timezone.now() - timedelta(days=int(periode))
        qs_transfer = qs_transfer.filter(waktu__gte=batas)
        qs_topup    = qs_topup.filter(waktu_proses__gte=batas)

    if teller_filter:
        qs_transfer = qs_transfer.filter(diproses_oleh_id=teller_filter)
        qs_topup    = qs_topup.filter(diproses_oleh_id=teller_filter)

    return qs_transfer, qs_topup


def _hitung_ringkasan(qs_transfer: QuerySet, qs_topup: QuerySet) -> dict:
    """Hitung agregasi dari queryset laporan yang sudah difilter."""
    return {
        'total_transfer':  qs_transfer.filter(jenis='transfer').aggregate(t=Sum('nominal'))['t'] or 0,
        'total_topup':     qs_topup.aggregate(t=Sum('nominal'))['t'] or 0,
        'jumlah_transfer': qs_transfer.filter(jenis='transfer').count(),
        'jumlah_topup':    qs_topup.count(),
    }

def _jalankan_verifikasi(request, form, objek, fungsi_operasi, url_redirect: str):
    """
    Pola generik untuk view verifikasi (approve/reject).
    Memanggil fungsi_operasi(objek, petugas, disetujui, catatan).
    """
    if request.method == 'POST' and form.is_valid():
        disetujui = form.cleaned_data['keputusan'] == 'approve'
        catatan  = bleach.clean(form.cleaned_data.get('catatan', ''), tags=[], strip=True)
        try:
            fungsi_operasi(objek, request.user, disetujui=disetujui, catatan=catatan)
            label = 'disetujui' if disetujui else 'ditolak'
            messages.success(request, f'Berhasil {label}.')
        except ValueError as e:
            messages.error(request, str(e))
        return redirect(url_redirect)
    return None  # Lanjut render template

@login_required
@csrf_protect
@khusus_nasabah
def halaman_transfer(request):
    rekening = get_object_or_404(Rekening, pemilik=request.user, aktif=True)
    form = TransferForm(request.POST or None, rekening_asal=rekening)

    if request.method == 'POST' and form.is_valid():
        nominal    = form.cleaned_data['nominal']
        keterangan = bleach.clean(form.cleaned_data.get('keterangan', ''), tags=[], strip=True)
        Transaksi.objects.create(
            rekening_asal=rekening,
            rekening_tujuan=form.rekening_tujuan_obj,
            jenis='transfer',
            nominal=nominal,
            keterangan=keterangan,
            status='pending',
        )
        from decimal import Decimal
        pesan = (
            'Transfer berhasil diajukan dan menunggu verifikasi Teller.'
            if nominal < Decimal('10000000')
            else 'Transfer >= Rp 10.000.000 memerlukan persetujuan Supervisor Bank.'
        )
        messages.success(request, pesan)
        return redirect('banking:mutasi')

    return render(request, 'banking/transfer.html', {'form': form, 'rekening': rekening})

@never_cache
@login_required
@khusus_nasabah
def halaman_mutasi(request):
    try:
        rekening = Rekening.objects.get(pemilik=request.user)
    except Rekening.DoesNotExist:
        messages.error(request, 'Rekening tidak ditemukan.')
        return redirect('accounts:dashboard')

    builder = (
        QueryRiwayat(rekening)
        .filter_rentang(request.GET.get('periode', '30'))
        .filter_jenis(request.GET.get('jenis', ''))
        .urutkan()
    )
    ringkasan = builder.ringkasan_nominal()

    return render(request, 'banking/mutasi.html', {
        'rekening':    rekening,
        'transaksi':   builder.hasil(),
        'filter_form': MutasiFilterForm(request.GET or None),
        **ringkasan,
    })

@login_required
@csrf_protect
@khusus_nasabah
def halaman_topup(request):
    rekening = get_object_or_404(Rekening, pemilik=request.user, aktif=True)
    form = TopUpForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        TopUp.objects.create(
            rekening=rekening,
            nominal=form.cleaned_data['nominal'],
            metode=form.cleaned_data['metode'],
            status='pending',
        )
        messages.success(request, 'Permintaan top-up berhasil diajukan. Teller akan segera memprosesnya.')
        return redirect('banking:mutasi')

    return render(request, 'banking/topup.html', {'form': form, 'rekening': rekening})


@login_required
@khusus_nasabah
def halaman_riwayat_topup(request):
    rekening  = get_object_or_404(Rekening, pemilik=request.user)
    topup_list = TopUp.objects.filter(rekening=rekening)
    return render(request, 'banking/riwayat_topup.html', {
        'rekening': rekening, 'topup_list': topup_list
    })

@login_required
@khusus_staf
def halaman_antrian_setor(request):
    pending, selesai = _query_antrian_setor(request.user)
    return render(request, 'banking/antrian_topup.html', {
        'pending': pending, 'selesai': selesai
    })


@login_required
@csrf_protect
@khusus_staf
def halaman_proses_setor(request, topup_id):
    topup = get_object_or_404(TopUp, pk=topup_id, status='pending')
    form  = ApprovalForm(request.POST or None)

    hasil = _jalankan_verifikasi(request, form, topup, operasi.jalankan_topup, 'banking:antrian_topup')
    if hasil:
        return hasil

    return render(request, 'banking/proses_topup.html', {'topup': topup, 'form': form})


@login_required
@khusus_staf
def halaman_antrian_kirim(request):
    pending, selesai = _query_antrian_kirim(request.user)
    return render(request, 'banking/antrian_transfer.html', {
        'pending': pending, 'selesai': selesai
    })

@login_required
@csrf_protect
@khusus_staf
def halaman_proses_kirim(request, transaksi_id):
    transaksi = get_object_or_404(Transaksi, pk=transaksi_id, jenis='transfer', status='pending')

    if transaksi.butuh_supervisor and request.user.is_teller:
        messages.error(request, 'Transfer ini memerlukan persetujuan Supervisor.')
        return redirect('banking:antrian_transfer')

    form  = ApprovalForm(request.POST or None)
    hasil = _jalankan_verifikasi(request, form, transaksi, operasi.jalankan_transfer, 'banking:antrian_transfer')
    if hasil:
        return hasil

    return render(request, 'banking/proses_transfer.html', {'transaksi': transaksi, 'form': form})

@login_required
@khusus_supervisor
def halaman_laporan(request):
    from accounts.models import CustomUser
    qs_transfer, qs_topup = _bangun_queryset_laporan(request.GET)
    ringkasan = _hitung_ringkasan(qs_transfer, qs_topup)

    return render(request, 'banking/laporan.html', {
        'transaksi':     qs_transfer.order_by('-waktu')[:50],
        'tellers':       CustomUser.objects.filter(role='teller'),
        'periode':       request.GET.get('periode', '30'),
        'teller_filter': request.GET.get('teller', ''),
        **ringkasan,
    })


@login_required
@khusus_supervisor
def halaman_kelola_rekening(request):
    from django.db.models import Q
    q = request.GET.get('q', '')
    qs = Rekening.objects.select_related('pemilik').all()
    if q:
        qs = qs.filter(
            Q(nomor_rekening__icontains=q)
            | Q(pemilik__first_name__icontains=q)
            | Q(pemilik__last_name__icontains=q)
            | Q(pemilik__username__icontains=q)
        )
    return render(request, 'banking/kelola_rekening.html', {'rekening_list': qs, 'q': q})


@login_required
@csrf_protect
@khusus_supervisor
def aksi_toggle_rekening(request, rekening_id):
    if request.method == 'POST':
        rekening = get_object_or_404(Rekening, pk=rekening_id)
        rekening.aktif = not rekening.aktif
        rekening.save()
        status = 'diaktifkan' if rekening.aktif else 'dinonaktifkan'
        messages.success(request, f'Rekening {rekening.nomor_rekening} berhasil {status}.')
    return redirect('banking:kelola_rekening')

@login_required
def halaman_notifikasi(request):
    notif_list = Notifikasi.objects.filter(user=request.user)
    notif_list.filter(dibaca=False).update(dibaca=True)
    return render(request, 'banking/notifikasi.html', {'notif_list': notif_list})

@login_required
@transaction.atomic 
def transfer(request):
    if request.method == 'POST':
        try:
            nominal = Decimal(request.POST.get('nominal', '0')) 
            if nominal <= 0: 
                raise ValueError 
        except (ValueError, InvalidOperation): 
            return HttpResponseBadRequest('Nominal tidak valid') 

        rek_tujuan_num = request.POST.get('rekening_tujuan')

        try:
            asal = request.user.rekening 
            tujuan = Rekening.objects.get(nomor_rekening=rek_tujuan_num) 

            if asal.saldo >= nominal: 
                asal.saldo -= nominal 
                tujuan.saldo += nominal 
                asal.save() 
                tujuan.save() 

                Transaksi.objects.create(
                    rekening_asal=asal,
                    rekening_tujuan=tujuan,
                    nominal=nominal,
                    jenis='transfer',
                    status='approved'
                )
                return redirect('banking:mutasi')
            else:
                return HttpResponseBadRequest('Saldo tidak mencukupi')
        except Rekening.DoesNotExist:
            return HttpResponseBadRequest('Rekening tujuan tidak ditemukan')
            
    return render(request, 'banking/transfer.html')

@login_required
def mutasi_rekening(request):
    riwayat = Transaksi.objects.filter(rekening_asal=request.user.rekening).order_by('-waktu')
    return render(request, 'banking/mutasi.html', {'transaksi': riwayat})

def cari_rekening_manual(nomor):
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT * FROM banking_rekening WHERE nomor_rekening = %s', 
            [nomor]
        )
        return cursor.fetchone()