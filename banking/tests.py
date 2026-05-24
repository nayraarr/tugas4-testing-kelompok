from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from decimal import Decimal
from django.contrib.auth import get_user_model
from banking.models import Rekening, Transaksi, TopUp
from banking.views import cari_rekening_manual, transfer, halaman_kelola_rekening, halaman_mutasi, halaman_antrian_kirim
from banking.views import halaman_laporan, mutasi_rekening
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from banking.validators import validate_safe_input
import bleach
from accounts.models import CustomUser
from banking.validators import validate_nominal, validate_no_rekening

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

# SQL Injection Prevention Test
class SQLTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username='nasabah_sqli_test', password='Password123!', role='nasabah'
        )
        self.rekening = Rekening.objects.create(
            pemilik=self.user,
            nomor_rekening='1234567890',
            saldo=Decimal('100000'),
            aktif=True,
        )
        # Supervisor
        self.supervisor = get_user_model().objects.create_user(
            username='supervisor_sqli_test', password='Password123!', role='supervisor'
        )
        # Rekening tujuan (dipakai oleh test transfer tambahan)
        self.user2 = get_user_model().objects.create_user(
            username='nasabah_tujuan', password='Password123!', role='nasabah'
        )
        self.rekening2 = Rekening.objects.create(
            pemilik=self.user2,
            nomor_rekening='2222222222',
            saldo=Decimal('0'),
            aktif=True,
        )
        # Teller
        self.teller = get_user_model().objects.create_user(
            username='teller_sqli_test', password='Password123!', role='teller'
        )
        # Seed transaksi agar query laporan tidak kosong
        Transaksi.objects.create(
            rekening_asal=self.rekening,
            rekening_tujuan=self.rekening2,
            nominal=Decimal('10000'),
            jenis='transfer',
            status='approved',
            diproses_oleh=self.teller,
        )
 
    def test_cari_rekening_manual_dengan_payload_sqli(self):
        """Uji apakah fungsi cari_rekening_manual kebal terhadap bypass SQL Injection."""
        malicious_payload = "1234567890' OR '1'='1"
        hasil = cari_rekening_manual(malicious_payload)
        self.assertIsNone(
            hasil,
            "Peringatan: Celah SQL Injection terdeteksi! Logika query berhasil dimanipulasi."
        )
 
    def test_cari_rekening_manual_dengan_input_valid(self):
        """Memastikan fungsi tetap bekerja normal untuk input yang valid."""
        hasil = cari_rekening_manual('1234567890')
        self.assertIsNotNone(hasil)
        self.assertIn('1234567890', hasil)
 
    def test_transfer_raw_post_input_with_sqli_payload(self):
        """Menembak fungsi transfer (POST) dengan payload SQLi pada rekening_tujuan."""
        request = self.factory.post('/banking/transfer/', {
            'nominal': '50000',
            'rekening_tujuan': "1234567890' OR '1'='1",
        })
        request.user = self.user
        response = transfer(request)
        self.assertEqual(response.status_code, 400)
 
    def test_transfer_nominal_sqli_payload_ditolak(self):
        """Nominal berisi string SQLi harus ditolak dengan 400."""
        request = self.factory.post('/banking/transfer/', {
            'nominal': "1 OR 1=1",
            'rekening_tujuan': self.rekening2.nomor_rekening,
        })
        request.user = self.user
        response = transfer(request)
        self.assertEqual(
            response.status_code, 400,
            "Payload SQLi pada nominal seharusnya menghasilkan 400 Bad Request."
        )
 
    def test_transfer_nominal_negatif_ditolak(self):
        """Nominal negatif atau nol tidak boleh lolos"""
        for nilai in ['-50000', '0', '-1']:
            with self.subTest(nominal=nilai):
                request = self.factory.post('/banking/transfer/', {
                    'nominal': nilai,
                    'rekening_tujuan': self.rekening2.nomor_rekening,
                })
                request.user = self.user
                response = transfer(request)
                self.assertEqual(
                    response.status_code, 400,
                    f"Nominal '{nilai}' seharusnya ditolak dengan 400."
                )
 
    def test_transfer_nominal_float_string_rekening_tidak_ada(self):
        """Saldo tidak boleh berubah jika rekening tujuan tidak valid, meski nominal float string valid secara Decimal."""
        saldo_awal = Rekening.objects.get(pk=self.rekening.pk).saldo
        request = self.factory.post('/banking/transfer/', {
            'nominal': '50000.99',
            'rekening_tujuan': '9999999999',
        })
        request.user = self.user
        response = transfer(request)
        self.assertEqual(response.status_code, 400)
        saldo_akhir = Rekening.objects.get(pk=self.rekening.pk).saldo
        self.assertEqual(
            saldo_awal, saldo_akhir,
            "Saldo tidak boleh berubah ketika transaksi gagal."
        )
 
    def test_transfer_rekening_tujuan_union_select_ditolak(self):
        """Payload UNION SELECT pada rekening_tujuan harus menghasilkan 400."""
        request = self.factory.post('/banking/transfer/', {
            'nominal': '10000',
            'rekening_tujuan': "' UNION SELECT username,password FROM accounts_customuser --",
        })
        request.user = self.user
        response = transfer(request)
        self.assertEqual(response.status_code, 400)
 
    def test_halaman_kelola_rekening_search_with_sqli_payload(self):
        """Menembak kolom pencarian supervisor dengan payload SQLi."""
        request = self.factory.get('/banking/kelola-rekening/', {
            'q': "' UNION SELECT * FROM accounts_customuser --",
        })
        request.user = self.supervisor
        response = halaman_kelola_rekening(request)
        self.assertEqual(response.status_code, 200)
 
    def test_halaman_mutasi_filter_jenis_with_sqli_payload(self):
        """Menembak parameter filter 'jenis' mutasi dengan payload SQLi."""
        request = self.factory.get('/banking/mutasi/', {
            'periode': 'all',
            'jenis': "' OR '1'='1",
        })
        request.user = self.user
        response = halaman_mutasi(request)
        self.assertEqual(response.status_code, 200)
 
    def test_halaman_mutasi_filter_periode_invalid_handled(self):
        """Memastikan input non-integer pada 'periode' mutasi ditolak/aman dari manipulasi."""
        request = self.factory.get('/banking/mutasi/', {
            'periode': "30; DROP TABLE banking_rekening --",
            'jenis': "",
        })
        request.user = self.user
        with self.assertRaises(ValueError):
            halaman_mutasi(request)
 
    def test_mutasi_rekening_user_tanpa_rekening_tidak_tampilkan_data_lain(self):
        """Jika user tidak memiliki rekening, view tidak boleh menampilkan data milik user lain"""
        user_baru = get_user_model().objects.create_user(
            username='user_tanpa_rek', password='Password123!', role='nasabah'
        )
        request = self.factory.get('/banking/mutasi-rekening/')
        request.user = user_baru
        with self.assertRaises(Exception):
            mutasi_rekening(request)
 
    def test_laporan_periode_drop_table_aman(self):
        """Param 'periode' berisi DROP TABLE harus menyebabkan ValueError sebelum menyentuh database."""
        request = self.factory.get('/banking/laporan/', {
            'periode': "30; DROP TABLE banking_transaksi --",
            'teller': '',
        })
        request.user = self.supervisor
        with self.assertRaises(ValueError):
            halaman_laporan(request)
 
    def test_laporan_periode_union_select_aman(self):
        """Payload UNION SELECT pada 'periode' harus gagal di konversi int(),"""
        request = self.factory.get('/banking/laporan/', {
            'periode': "' UNION SELECT * FROM accounts_customuser --",
        })
        request.user = self.supervisor
        with self.assertRaises(ValueError):
            halaman_laporan(request)
 
    def test_laporan_teller_filter_sqli_payload_aman(self):
        """Param 'teller' diteruskan ke filter(diproses_oleh_id=...). Django ORM harus raise ValueError/Exception"""
        request = self.factory.get('/banking/laporan/', {
            'periode': '30',
            'teller': "1 OR 1=1",
        })
        request.user = self.supervisor
        with self.assertRaises((ValueError, Exception)):
            halaman_laporan(request)
 
    def test_laporan_periode_valid_200(self):
        """Laporan dengan parameter valid harus tetap mengembalikan 200."""
        request = self.factory.get('/banking/laporan/', {
            'periode': '30',
            'teller': '',
        })
        request.user = self.supervisor
        response = halaman_laporan(request)
        self.assertEqual(response.status_code, 200)
 
    def test_laporan_periode_all_valid_200(self):
        """Laporan dengan periode='all' harus tetap mengembalikan 200."""
        request = self.factory.get('/banking/laporan/', {
            'periode': 'all',
            'teller': '',
        })
        request.user = self.supervisor
        response = halaman_laporan(request)
        self.assertEqual(response.status_code, 200)
 
    def test_antrian_kirim_teller_hanya_lihat_dibawah_10juta(self):
        """Teller hanya boleh melihat transaksi pending < 10.000.000. Transaksi >= 10jt tidak boleh ada di antrian teller."""
        Transaksi.objects.create(
            rekening_asal=self.rekening,
            rekening_tujuan=self.rekening2,
            nominal=Decimal('15000000'),
            jenis='transfer',
            status='pending',
        )
        self.client.force_login(self.teller)
        response = self.client.get('/banking/antrian-transfer/')
        self.assertEqual(response.status_code, 200)
        pending_ctx = list(response.context['pending'])
        for trx in pending_ctx:
            self.assertLess(
                trx.nominal,
                Decimal('10000000'),
                "Teller tidak boleh melihat transaksi >= 10 juta di antriannya."
            )
 
    def test_antrian_kirim_supervisor_lihat_semua(self):
        """Supervisor harus bisa melihat semua transaksi pending termasuk yang >= 10 juta."""
        Transaksi.objects.create(
            rekening_asal=self.rekening,
            rekening_tujuan=self.rekening2,
            nominal=Decimal('20000000'),
            jenis='transfer',
            status='pending',
        )
        self.client.force_login(self.supervisor)
        response = self.client.get('/banking/antrian-transfer/')
        self.assertEqual(response.status_code, 200)
        pending_ctx = list(response.context['pending'])
        nominal_list = [t.nominal for t in pending_ctx]
        self.assertTrue(
            any(n >= Decimal('10000000') for n in nominal_list),
            "Supervisor harus melihat transaksi >= 10 juta di antrian."
        )
 
    def test_antrian_kirim_get_param_sqli_tidak_merusak_query(self):
        """GET parameter asing / SQLi pada URL antrian tidak boleh merusak query ORM maupun mengembalikan error 500."""
        request = self.factory.get(
            '/banking/antrian-transfer/',
            {'q': "' OR '1'='1"},
        )
        request.user = self.teller
        response = halaman_antrian_kirim(request)
        self.assertEqual(
            response.status_code, 200,
            "Param asing pada GET tidak boleh menyebabkan error 500."
        )

# CODE INJECTION PREVENTION TESTS
class ValidateSafeInputTests(TestCase):
    """Unit test untuk fungsi validate_safe_input()"""

    # --- TC-CI-01: Script Tag / XSS ---
    def test_tolak_script_tag(self):
        """Input <script>alert('XSS')</script> harus ditolak."""
        with self.assertRaises(ValidationError):
            validate_safe_input("<script>alert('XSS')</script>")

    def test_tolak_script_tag_reflected(self):
        """Input dengan tag <script> apapun harus ditolak."""
        with self.assertRaises(ValidationError):
            validate_safe_input("<script src='evil.js'></script>")

    # --- TC-CI-02: HTML Injection ---
    def test_tolak_html_injection_h1(self):
        """Input <h1>Hacked</h1> harus ditolak."""
        with self.assertRaises(ValidationError):
            validate_safe_input("<h1>Hacked</h1>")

    def test_tolak_html_injection_img_onerror(self):
        """Input <img src=x onerror=alert(1)> harus ditolak."""
        with self.assertRaises(ValidationError):
            validate_safe_input("<img src=x onerror=alert(1)>")

    # --- TC-CI-03: Template Injection / SSTI ---
    def test_tolak_template_injection_kalkulasi(self):
        """Input {{7*7}} harus ditolak karena karakter { dan }."""
        with self.assertRaises(ValidationError):
            validate_safe_input("{{7*7}}")

    def test_tolak_template_injection_secret_key(self):
        """Input {{config.SECRET_KEY}} harus ditolak."""
        with self.assertRaises(ValidationError):
            validate_safe_input("{{config.SECRET_KEY}}")

    # --- Input valid harus lolos ---
    def test_terima_input_normal(self):
        """Input teks biasa harus lolos validasi."""
        try:
            validate_safe_input("Bayar makan siang")
        except ValidationError:
            self.fail("Input normal seharusnya tidak ditolak.")

    def test_terima_input_angka(self):
        """Input angka harus lolos validasi."""
        try:
            validate_safe_input("Transfer 500000")
        except ValidationError:
            self.fail("Input angka seharusnya tidak ditolak.")

    # --- Karakter berbahaya lainnya ---
    def test_tolak_karakter_ampersand(self):
        """Input dengan & harus ditolak."""
        with self.assertRaises(ValidationError):
            validate_safe_input("test & inject")

    def test_tolak_karakter_semicolon(self):
        """Input dengan ; harus ditolak (SQL/code separator)."""
        with self.assertRaises(ValidationError):
            validate_safe_input("test; DROP TABLE")

    def test_tolak_karakter_single_quote(self):
        """Input dengan ' harus ditolak."""
        with self.assertRaises(ValidationError):
            validate_safe_input("' OR '1'='1")


class BleachSanitasiTests(TestCase):
    """Unit test untuk sanitasi output dengan bleach.clean()"""

    def test_bleach_strip_script_tag(self):
        """bleach.clean() harus menghapus tag <script>."""
        hasil = bleach.clean("<script>alert('XSS')</script>", tags=[], strip=True)
        self.assertNotIn("<script>", hasil)
        self.assertNotIn("</script>", hasil)

    def test_bleach_strip_html_tag(self):
        """bleach.clean() harus menghapus tag HTML apapun."""
        hasil = bleach.clean("<h1>Hacked</h1>", tags=[], strip=True)
        self.assertNotIn("<h1>", hasil)
        self.assertEqual(hasil, "Hacked")

    def test_bleach_strip_img_onerror(self):
        """bleach.clean() harus menghapus tag img dengan onerror."""
        hasil = bleach.clean("<img src=x onerror=alert(1)>", tags=[], strip=True)
        self.assertNotIn("<img", hasil)
        self.assertNotIn("onerror", hasil)

    def test_bleach_teks_normal_tidak_berubah(self):
        """bleach.clean() tidak boleh mengubah teks biasa."""
        input_normal = "Bayar makan siang"
        hasil = bleach.clean(input_normal, tags=[], strip=True)
        self.assertEqual(hasil, input_normal)

class CodeInjectionTransferTests(TestCase):
    """TC-CI-04c: Injeksi pada field keterangan transfer"""

    def setUp(self):
        # Buat user nasabah
        self.nasabah = CustomUser.objects.create_user(
            username='testnasabah', password='password123',
            first_name='Test', last_name='Nasabah',
            email='test@mail.com', role='nasabah',
        )
        # Buat rekening asal
        self.rekening_asal = Rekening.objects.create(
            pemilik=self.nasabah,
            nomor_rekening='1234567890',
            saldo=Decimal('1000000'),
        )
        # Buat rekening tujuan
        self.nasabah2 = CustomUser.objects.create_user(
            username='testnasabah2', password='password123',
            first_name='Test2', last_name='Nasabah2',
            email='test2@mail.com', role='nasabah',
        )
        self.rekening_tujuan = Rekening.objects.create(
            pemilik=self.nasabah2,
            nomor_rekening='0987654321',
            saldo=Decimal('500000'),
        )

    def test_keterangan_xss_ditolak_validator(self):
        """TC-CI-04c: <script>alert('transfer intercepted')</script> harus ditolak validator."""
        # Ganti self.client.login dengan force_login
        self.client.force_login(self.nasabah)
        
        response = self.client.post('/banking/transfer/', {
            'rekening_tujuan': '0987654321',
            'nominal': '10000',
            'keterangan': "<script>alert('transfer intercepted')</script>",
        })
        # Form harus ditolak, transaksi tidak terbuat
        from banking.models import Transaksi
        transaksi_ada = Transaksi.objects.filter(
            rekening_asal=self.rekening_asal
        ).exists()
        self.assertFalse(transaksi_ada, "Transaksi tidak boleh terbuat jika keterangan mengandung XSS payload.")

class ValidateNominalTests(TestCase):
    """Unit test untuk fungsi validate_nominal()"""

    def test_tolak_nominal_nol(self):
        """Nominal 0 harus ditolak."""
        with self.assertRaises(ValidationError):
            validate_nominal(Decimal('0'))

    def test_tolak_nominal_negatif(self):
        """Nominal negatif harus ditolak."""
        with self.assertRaises(ValidationError):
            validate_nominal(Decimal('-1000'))

    def test_tolak_nominal_melebihi_batas(self):
        """Nominal di atas 1 miliar harus ditolak."""
        with self.assertRaises(ValidationError):
            validate_nominal(Decimal('1000000001'))

    def test_terima_nominal_valid(self):
        """Nominal positif normal harus lolos."""
        try:
            validate_nominal(Decimal('50000'))
        except ValidationError:
            self.fail("Nominal valid seharusnya tidak ditolak.")


class ValidateNoRekeningTests(TestCase):
    """Unit test untuk fungsi validate_no_rekening()"""

    def test_tolak_bukan_angka(self):
        """Nomor rekening yang mengandung huruf harus ditolak."""
        with self.assertRaises(ValidationError):
            validate_no_rekening("123ABC7890")

    def test_tolak_kurang_dari_10_digit(self):
        """Nomor rekening kurang dari 10 digit harus ditolak."""
        with self.assertRaises(ValidationError):
            validate_no_rekening("12345")

    def test_tolak_lebih_dari_10_digit(self):
        """Nomor rekening lebih dari 10 digit harus ditolak."""
        with self.assertRaises(ValidationError):
            validate_no_rekening("12345678901")

    def test_terima_no_rekening_valid(self):
        """Nomor rekening 10 digit angka harus lolos."""
        try:
            validate_no_rekening("1234567890")
        except ValidationError:
            self.fail("Nomor rekening valid seharusnya tidak ditolak.")