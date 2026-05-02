import random
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Rekening, Transaksi, TopUp, Notifikasi


def _generate_nomor_rekening():
    while True:
        nomor = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        if not Rekening.objects.filter(nomor_rekening=nomor).exists():
            return nomor


def buat_rekening_baru(user, saldo_awal=Decimal('0.00')):
    nomor = _generate_nomor_rekening()
    rekening = Rekening.objects.create(
        nomor_rekening=nomor,
        pemilik=user,
        saldo=saldo_awal,
    )
    Notifikasi.objects.create(
        user=user,
        pesan=f'Rekening Anda berhasil dibuat dengan nomor {nomor}.',
        link='/banking/mutasi/',
    )
    return rekening


@transaction.atomic
def proses_transfer(transaksi, staff_user, disetujui=True, catatan=''):
    transaksi = Transaksi.objects.select_for_update().get(pk=transaksi.pk)
    if transaksi.status != 'pending':
        raise ValueError('Transaksi sudah diproses sebelumnya.')

    transaksi.diproses_oleh = staff_user
    transaksi.waktu_diproses = timezone.now()
    transaksi.catatan_staff = catatan

    if disetujui:
        asal = Rekening.objects.select_for_update().get(pk=transaksi.rekening_asal.pk)
        tujuan = Rekening.objects.select_for_update().get(pk=transaksi.rekening_tujuan.pk)

        if asal.saldo < transaksi.nominal:
            transaksi.status = 'rejected'
            transaksi.catatan_staff = 'Saldo tidak mencukupi saat proses approval.'
            transaksi.save()
            raise ValueError('Saldo nasabah tidak mencukupi.')

        asal.saldo -= transaksi.nominal
        tujuan.saldo += transaksi.nominal
        asal.save()
        tujuan.save()
        transaksi.status = 'approved'

        Notifikasi.objects.create(
            user=asal.pemilik,
            pesan=f'Transfer Rp {transaksi.nominal:,.0f} ke {tujuan.nomor_rekening} telah disetujui.',
            link='/banking/mutasi/',
        )
        Notifikasi.objects.create(
            user=tujuan.pemilik,
            pesan=f'Anda menerima transfer Rp {transaksi.nominal:,.0f} dari {asal.nomor_rekening}.',
            link='/banking/mutasi/',
        )
    else:
        transaksi.status = 'rejected'
        Notifikasi.objects.create(
            user=transaksi.rekening_asal.pemilik,
            pesan=f'Transfer Rp {transaksi.nominal:,.0f} ditolak. Alasan: {catatan}',
            link='/banking/mutasi/',
        )

    transaksi.save()
    return transaksi


@transaction.atomic
def proses_topup(topup, teller_user, disetujui=True, catatan=''):
    topup = TopUp.objects.select_for_update().get(pk=topup.pk)
    if topup.status != 'pending':
        raise ValueError('Top-up sudah diproses.')

    topup.diproses_oleh = teller_user
    topup.waktu_proses = timezone.now()
    topup.keterangan = catatan

    if disetujui:
        rekening = Rekening.objects.select_for_update().get(pk=topup.rekening.pk)
        rekening.saldo += topup.nominal
        rekening.save()
        topup.status = 'selesai'

        # Catat sebagai transaksi topup
        Transaksi.objects.create(
            rekening_tujuan=rekening,
            jenis='topup',
            nominal=topup.nominal,
            status='approved',
            diproses_oleh=teller_user,
            waktu_diproses=timezone.now(),
            keterangan=f'Top-up via {topup.get_metode_display()}',
        )
        Notifikasi.objects.create(
            user=rekening.pemilik,
            pesan=f'Top-up Rp {topup.nominal:,.0f} berhasil. Saldo Anda: Rp {rekening.saldo:,.0f}.',
            link='/banking/mutasi/',
        )
    else:
        topup.status = 'ditolak'
        Notifikasi.objects.create(
            user=topup.rekening.pemilik,
            pesan=f'Permintaan top-up Rp {topup.nominal:,.0f} ditolak. Alasan: {catatan}',
        )

    topup.save()
    return topup
