from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from banking.models import Rekening
from banking.views import cari_rekening_manual

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

# SQL Injection Prevention Test
class SQLTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='nasabah_sqli_test', password='Password123!', role='nasabah'
        )
        self.rekening = Rekening.objects.create(
            pemilik=self.user, nomor_rekening='1234567890', saldo=100000, aktif=True
        )

    def test_cari_rekening_manual_dengan_payload_sqli(self):
        """Uji apakah fungsi cari_rekening_manual kebal terhadap bypass SQL Injection"""
        malicious_payload = "1234567890' OR '1'='1"
        hasil = cari_rekening_manual(malicious_payload)
        self.assertIsNone(hasil, "Peringatan: Celah SQL Injection terdeteksi! Logika query berhasil dimanipulasi.")

    def test_cari_rekening_manual_dengan_input_valid(self):
        """Memastikan fungsi tetap bekerja normal untuk input yang valid"""
        hasil = cari_rekening_manual('1234567890')
        self.assertIsNotNone(hasil)
        self.assertIn('1234567890', hasil)