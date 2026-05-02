from decimal import Decimal
from pyexpat.errors import messages

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required

from accounts.decorators import nasabah_only
from banking.forms import TransferForm
from banking.models import Rekening

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