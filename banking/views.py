from datetime import timedelta, timezone
from decimal import Decimal
from pyexpat.errors import messages

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required

from accounts.decorators import nasabah_only, staff_only
from banking import services
from banking.forms import ApprovalForm, MutasiFilterForm, TransferForm
from banking.models import Rekening, TopUp, Transaksi

@login_required
@nasabah_only
def transfer_view(request):
    rekening = get_object_or_404(Rekening, pemilik=request.user, aktif=True)
    form = TransferForm(request.POST or None, rekening_asal=rekening)

    if request.method == 'POST' and form.is_valid():
        tujuan = form.rekening_tujuan_obj
        nominal = form.cleaned_data['nominal']
        keterangan = form.cleaned_data.get('keterangan', '')

        transaksi = Transaksi.objects.create(
            rekening_asal=rekening,
            rekening_tujuan=tujuan,
            jenis='transfer',
            nominal=nominal,
            keterangan=keterangan,
            status='pending',
        )
        # Langsung approve jika < 10 juta (tidak butuh supervisor)
        if nominal < Decimal('10000000'):
            msg = 'Transfer berhasil diajukan dan menunggu verifikasi Teller.'
        else:
            msg = 'Transfer >= Rp 10.000.000 memerlukan persetujuan Supervisor Bank.'
        messages.success(request, msg)
        return redirect('banking:mutasi')

    return render(request, 'banking/transfer.html', {'form': form, 'rekening': rekening})

@login_required
@nasabah_only
def mutasi_view(request):
    rekening = get_object_or_404(Rekening, pomilik=request.user) if False else None
    try:
        rekening = Rekening.objects.get(pemilik=request.user)
    except Rekening.DoesNotExist:
        messages.error(request, 'Rekening tidak ditemukan.')
        return redirect('accounts:dashboard')

    filter_form = MutasiFilterForm(request.GET or None)
    transaksi = Transaksi.objects.filter(
        Q(rekening_asal=rekening) | Q(rekening_tujuan=rekening)
    )

    if filter_form.is_valid() or request.GET:
        periode = request.GET.get('periode', '30')
        jenis = request.GET.get('jenis', '')
        if periode and periode != 'all':
            cutoff = timezone.now() - timedelta(days=int(periode))
            transaksi = transaksi.filter(waktu__gte=cutoff)
        if jenis:
            transaksi = transaksi.filter(jenis=jenis)

    transaksi = transaksi.order_by('-waktu')

    total_masuk = transaksi.filter(rekening_tujuan=rekening, status='approved').aggregate(t=Sum('nominal'))['t'] or 0
    total_keluar = transaksi.filter(rekening_asal=rekening, status='approved').aggregate(t=Sum('nominal'))['t'] or 0

    return render(request, 'banking/mutasi.html', {
        'rekening': rekening,
        'transaksi': transaksi,
        'filter_form': filter_form,
        'total_masuk': total_masuk,
        'total_keluar': total_keluar,
    })

@login_required
@nasabah_only
def topup_view(request):
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
@nasabah_only
def riwayat_topup_view(request):
    rekening = get_object_or_404(Rekening, pemilik=request.user)
    topup_list = TopUp.objects.filter(rekening=rekening)
    return render(request, 'banking/riwayat_topup.html', {'rekening': rekening, 'topup_list': topup_list})

@login_required
@staff_only
def antrian_topup_view(request):
    pending = TopUp.objects.filter(status='pending').select_related('rekening__pemilik')
    selesai = TopUp.objects.exclude(status='pending').select_related('rekening__pemilik', 'diproses_oleh')[:20]
    return render(request, 'banking/antrian_topup.html', {'pending': pending, 'selesai': selesai})


@login_required
@staff_only
def proses_topup_view(request, topup_id):
    topup = get_object_or_404(TopUp, pk=topup_id, status='pending')
    form = ApprovalForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        disetujui = form.cleaned_data['keputusan'] == 'approve'
        catatan = form.cleaned_data.get('catatan', '')
        try:
            services.proses_topup(topup, request.user, disetujui=disetujui, catatan=catatan)
            status_msg = 'disetujui' if disetujui else 'ditolak'
            messages.success(request, f'Top-up berhasil {status_msg}.')
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('banking:antrian_topup')

    return render(request, 'banking/proses_topup.html', {'topup': topup, 'form': form})