import random
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import Rekening, Transaksi, TopUp, Notifikasi

def _hasilkan_nomor_rekening() -> str:
    """Hasilkan nomor rekening 10 digit yang belum terpakai."""
    while True:
        kandidat = ''.join(str(random.randint(0, 9)) for _ in range(10))
        if not Rekening.objects.filter(nomor_rekening=kandidat).exists():
            return kandidat

def _validasi_status(objek, status_diharapkan: str, label: str) -> None:
    if objek.status != status_diharapkan:
        raise ValueError(f'{label} sudah diproses sebelumnya.')


def _validasi_saldo_cukup(rekening: Rekening, nominal: Decimal) -> None:
    if rekening.saldo < nominal:
        raise ValueError('Saldo nasabah tidak mencukupi.')

def _eksekusi_debit_kredit(
    rekening_asal: Rekening,
    rekening_tujuan: Rekening,
    nominal: Decimal,
) -> None:
    rekening_asal.saldo -= nominal
    rekening_tujuan.saldo += nominal
    rekening_asal.save()
    rekening_tujuan.save()


def _eksekusi_kredit(rekening: Rekening, nominal: Decimal) -> None:
    rekening.saldo += nominal
    rekening.save()

def _notif_transfer_disetujui(
    pemilik_asal,
    pemilik_tujuan,
    nominal: Decimal,
    no_tujuan: str,
    no_asal: str,
) -> None:
    Notifikasi.objects.bulk_create([
        Notifikasi(
            user=pemilik_asal,
            pesan=f'Transfer Rp {nominal:,.0f} ke {no_tujuan} telah disetujui.',
            link='/banking/mutasi/',
        ),
        Notifikasi(
            user=pemilik_tujuan,
            pesan=f'Anda menerima transfer Rp {nominal:,.0f} dari {no_asal}.',
            link='/banking/mutasi/',
        ),
    ])


def _notif_transfer_ditolak(pemilik_asal, nominal: Decimal, alasan: str) -> None:
    Notifikasi.objects.create(
        user=pemilik_asal,
        pesan=f'Transfer Rp {nominal:,.0f} ditolak. Alasan: {alasan}',
        link='/banking/mutasi/',
    )


def _notif_topup_disetujui(pemilik, nominal: Decimal, saldo_baru: Decimal) -> None:
    Notifikasi.objects.create(
        user=pemilik,
        pesan=f'Top-up Rp {nominal:,.0f} berhasil. Saldo Anda: Rp {saldo_baru:,.0f}.',
        link='/banking/mutasi/',
    )


def _notif_topup_ditolak(pemilik, nominal: Decimal, alasan: str) -> None:
    Notifikasi.objects.create(
        user=pemilik,
        pesan=f'Permintaan top-up Rp {nominal:,.0f} ditolak. Alasan: {alasan}',
    )

def buat_rekening_baru(user, saldo_awal: Decimal = Decimal('0.00')) -> Rekening:
    nomor = _hasilkan_nomor_rekening()
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
def jalankan_transfer(transaksi: Transaksi, petugas, disetujui: bool, catatan: str = '') -> Transaksi:
    transaksi = Transaksi.objects.select_for_update().get(pk=transaksi.pk)
    _validasi_status(transaksi, 'pending', 'Transaksi')

    transaksi.diproses_oleh = petugas
    transaksi.waktu_diproses = timezone.now()
    transaksi.catatan_staff = catatan

    if disetujui:
        asal   = Rekening.objects.select_for_update().get(pk=transaksi.rekening_asal.pk)
        tujuan = Rekening.objects.select_for_update().get(pk=transaksi.rekening_tujuan.pk)

        try:
            _validasi_saldo_cukup(asal, transaksi.nominal)
        except ValueError:
            transaksi.status = 'rejected'
            transaksi.catatan_staff = 'Saldo tidak mencukupi saat proses approval.'
            transaksi.save()
            raise

        _eksekusi_debit_kredit(asal, tujuan, transaksi.nominal)
        transaksi.status = 'approved'
        _notif_transfer_disetujui(
            asal.pemilik, tujuan.pemilik,
            transaksi.nominal, tujuan.nomor_rekening, asal.nomor_rekening,
        )
    else:
        transaksi.status = 'rejected'
        
        # Pastikan rekening_asal ada sebelum akses
        if transaksi.rekening_asal:
            _notif_transfer_ditolak(
                transaksi.rekening_asal.pemilik, transaksi.nominal, catatan
            )

    transaksi.save()
    return transaksi


@transaction.atomic
def jalankan_topup(topup: TopUp, petugas, disetujui: bool, catatan: str = '') -> TopUp:
    topup = TopUp.objects.select_for_update().get(pk=topup.pk)
    _validasi_status(topup, 'pending', 'Top-up')

    topup.diproses_oleh = petugas
    topup.waktu_proses = timezone.now()
    topup.keterangan = catatan

    if disetujui:
        rekening = Rekening.objects.select_for_update().get(pk=topup.rekening.pk)
        _eksekusi_kredit(rekening, topup.nominal)
        topup.status = 'selesai'

        Transaksi.objects.create(
            rekening_tujuan=rekening,
            jenis='topup',
            nominal=topup.nominal,
            status='approved',
            diproses_oleh=petugas,
            waktu_diproses=timezone.now(),
            keterangan=f'Top-up via {topup.get_metode_display()}',
        )
        _notif_topup_disetujui(rekening.pemilik, topup.nominal, rekening.saldo)
    else:
        topup.status = 'ditolak'
        _notif_topup_ditolak(topup.rekening.pemilik, topup.nominal, catatan)

    topup.save()
    return topup
