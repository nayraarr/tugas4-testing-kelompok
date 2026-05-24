from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from django.contrib.auth import get_user_model
from banking.models import Rekening

from accounts.models import CustomUser
from banking.models import Rekening, TopUp, Transaksi

User = get_user_model()


def buat_nasabah(username, role='nasabah', password='Rahasia@Bank1!'):
    return User.objects.create_user(username=username, password=password, role=role)


def buat_rekening_nasabah(user, saldo=Decimal('5000000.00')):
    return Rekening.objects.create(
        nomor_rekening=f'REK{user.pk:07d}',
        pemilik=user,
        saldo=saldo,
        aktif=True,
    )

class BankingAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='nasabah_uji', password='Password123!', role='nasabah'
        )
        self.rekening = Rekening.objects.create(
            pemilik=self.user, nomor_rekening='1234567890', saldo=500000, aktif=True
        )

    def test_akses_halaman_transfer_tanpa_login(self):
        """Uji apakah guest bisa akses transfer (Harus Gagal/Redirect)"""
        response = self.client.get(reverse('banking:transfer'))
        self.assertEqual(response.status_code, 302) # Harus redirect ke login

    def test_proteksi_cache_halaman_mutasi(self):
        """Uji @never_cache pada mutasi (Mitigasi Back-Button Attack)"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('banking:mutasi'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-cache', response.get('Cache-Control', ''))
        self.assertIn('no-store', response.get('Cache-Control', ''))


class CSRFTransferTest(TestCase):
    def setUp(self):
        self.pengirim = buat_nasabah('budi_pengirim')
        self.rek_pengirim = buat_rekening_nasabah(self.pengirim, saldo=Decimal('5000000.00'))
        self.penerima = buat_nasabah('siti_penerima')
        self.rek_penerima = buat_rekening_nasabah(self.penerima, saldo=Decimal('0.00'))
        self.client_csrf = Client(enforce_csrf_checks=True)
        self.url = reverse('banking:transfer')

    def test_transfer_tanpa_token_csrf_ditolak(self):
        """POST transfer tanpa CSRF token harus ditolak (403)."""
        self.client_csrf.force_login(self.pengirim)
        response = self.client_csrf.post(self.url, {
            'rekening_tujuan': self.rek_penerima.nomor_rekening,
            'nominal': '100000',
            'keterangan': 'Transfer tanpa token csrf',
        })
        self.assertEqual(response.status_code, 403)

    def test_transfer_dengan_token_csrf_valid_diterima(self):
        """POST transfer dengan CSRF token valid harus diproses (bukan 403)."""
        self.client.force_login(self.pengirim)
        response = self.client.post(self.url, {
            'rekening_tujuan': self.rek_penerima.nomor_rekening,
            'nominal': '100000',
            'keterangan': 'Transfer dengan token csrf',
        })
        self.assertNotEqual(response.status_code, 403)

    def test_transfer_method_get_tidak_perlu_csrf(self):
        """GET ke halaman transfer tidak memerlukan CSRF token."""
        self.client_csrf.force_login(self.pengirim)
        response = self.client_csrf.get(self.url)
        self.assertNotEqual(response.status_code, 403)

    def test_transaksi_tidak_terbuat_jika_csrf_gagal(self):
        """Transaksi tidak boleh terbuat jika request ditolak karena CSRF."""
        self.client_csrf.force_login(self.pengirim)
        jumlah_sebelum = Transaksi.objects.count()
        self.client_csrf.post(self.url, {
            'rekening_tujuan': self.rek_penerima.nomor_rekening,
            'nominal': '100000',
        })
        self.assertEqual(Transaksi.objects.count(), jumlah_sebelum)

    def test_saldo_pengirim_tidak_berkurang_jika_csrf_gagal(self):
        """Saldo rekening tidak boleh berkurang kalau request CSRF ditolak."""
        self.client_csrf.force_login(self.pengirim)
        saldo_awal = self.rek_pengirim.saldo
        self.client_csrf.post(self.url, {
            'rekening_tujuan': self.rek_penerima.nomor_rekening,
            'nominal': '100000',
        })
        self.rek_pengirim.refresh_from_db()
        self.assertEqual(self.rek_pengirim.saldo, saldo_awal)


class CSRFTopUpTest(TestCase):
    def setUp(self):
        self.nasabah = buat_nasabah('andi_topup')
        self.rekening = buat_rekening_nasabah(self.nasabah)
        self.client_csrf = Client(enforce_csrf_checks=True)
        self.url = reverse('banking:topup')

    def test_topup_tanpa_token_csrf_ditolak(self):
        """POST top-up tanpa CSRF token harus ditolak (403)."""
        self.client_csrf.force_login(self.nasabah)
        response = self.client_csrf.post(self.url, {
            'nominal': '500000',
            'metode': 'tunai',
        })
        self.assertEqual(response.status_code, 403)

    def test_topup_dengan_token_csrf_valid_diterima(self):
        """POST top-up dengan CSRF token valid harus diproses."""
        self.client.force_login(self.nasabah)
        response = self.client.post(self.url, {
            'nominal': '500000',
            'metode': 'tunai',
        })
        self.assertNotEqual(response.status_code, 403)

    def test_topup_tidak_terbuat_jika_csrf_gagal(self):
        """Record TopUp tidak boleh terbuat jika CSRF gagal."""
        self.client_csrf.force_login(self.nasabah)
        jumlah_sebelum = TopUp.objects.count()
        self.client_csrf.post(self.url, {'nominal': '500000', 'metode': 'tunai'})
        self.assertEqual(TopUp.objects.count(), jumlah_sebelum)


class CSRFProsesTransferTest(TestCase):
    def setUp(self):
        self.petugas_teller = buat_nasabah('rini_teller', role='teller')
        self.nasabah_pengirim = buat_nasabah('dedi_pengirim')
        self.rek_pengirim = buat_rekening_nasabah(self.nasabah_pengirim)
        self.nasabah_penerima = buat_nasabah('maya_penerima')
        self.rek_penerima = buat_rekening_nasabah(self.nasabah_penerima)
        self.transaksi = Transaksi.objects.create(
            rekening_asal=self.rek_pengirim,
            rekening_tujuan=self.rek_penerima,
            jenis='transfer',
            nominal=Decimal('500000.00'),
            status='pending',
        )
        self.client_csrf = Client(enforce_csrf_checks=True)
        self.url = reverse('banking:proses_transfer', args=[self.transaksi.pk])

    def test_approve_transfer_tanpa_token_csrf_ditolak(self):
        """POST approve transfer tanpa CSRF token harus ditolak (403)."""
        self.client_csrf.force_login(self.petugas_teller)
        response = self.client_csrf.post(self.url, {
            'keputusan': 'approve',
            'catatan': '',
        })
        self.assertEqual(response.status_code, 403)

    def test_status_transaksi_tetap_pending_jika_csrf_gagal(self):
        """Status transaksi tidak boleh berubah jika CSRF gagal."""
        self.client_csrf.force_login(self.petugas_teller)
        self.client_csrf.post(self.url, {'keputusan': 'approve', 'catatan': ''})
        self.transaksi.refresh_from_db()
        self.assertEqual(self.transaksi.status, 'pending')


class CSRFProsesTopUpTest(TestCase):
    def setUp(self):
        self.petugas_teller = buat_nasabah('hendra_teller', role='teller')
        self.nasabah = buat_nasabah('dewi_setor')
        self.rekening = buat_rekening_nasabah(self.nasabah)
        self.topup = TopUp.objects.create(
            rekening=self.rekening,
            nominal=Decimal('200000.00'),
            metode='tunai',
            status='pending',
        )
        self.client_csrf = Client(enforce_csrf_checks=True)
        self.url = reverse('banking:proses_topup', args=[self.topup.pk])

    def test_approve_topup_tanpa_token_csrf_ditolak(self):
        """POST approve top-up tanpa CSRF token harus ditolak (403)."""
        self.client_csrf.force_login(self.petugas_teller)
        response = self.client_csrf.post(self.url, {
            'keputusan': 'approve',
            'catatan': '',
        })
        self.assertEqual(response.status_code, 403)

    def test_status_topup_tetap_pending_jika_csrf_gagal(self):
        """Status TopUp tidak boleh berubah jika CSRF gagal."""
        self.client_csrf.force_login(self.petugas_teller)
        self.client_csrf.post(self.url, {'keputusan': 'approve', 'catatan': ''})
        self.topup.refresh_from_db()
        self.assertEqual(self.topup.status, 'pending')

class CSRFToggleRekeningTest(TestCase):
    def setUp(self):
        self.pengawas = buat_nasabah('ahmad_supervisor', role='supervisor')
        self.nasabah = buat_nasabah('lina_nasabah')
        self.rekening = buat_rekening_nasabah(self.nasabah)
        self.client_csrf = Client(enforce_csrf_checks=True)
        self.url = reverse('banking:toggle_rekening', args=[self.rekening.pk])

    def test_toggle_rekening_tanpa_token_csrf_ditolak(self):
        """POST toggle rekening tanpa CSRF token harus ditolak (403)."""
        self.client_csrf.force_login(self.pengawas)
        response = self.client_csrf.post(self.url)
        self.assertEqual(response.status_code, 403)

    def test_status_rekening_tidak_berubah_jika_csrf_gagal(self):
        """Status aktif rekening tidak boleh berubah jika CSRF gagal."""
        self.client_csrf.force_login(self.pengawas)
        status_awal = self.rekening.aktif
        self.client_csrf.post(self.url)
        self.rekening.refresh_from_db()
        self.assertEqual(self.rekening.aktif, status_awal)
