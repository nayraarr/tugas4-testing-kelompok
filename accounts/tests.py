from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from axes.models import AccessAttempt

User = get_user_model()

@override_settings(
    SECRET_KEY='kunci_rahasia_untuk_keperluan_testing_12345',
    AXES_ENABLED=True,
    AXES_FAILURE_LIMIT=6
)

class BrokenAuthMitigationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.username = 'nasabahtest'
        self.password = 'SandiKuat123!'
        
        self.user = User.objects.create_user(
            username=self.username, 
            password=self.password,
            role='nasabah',
            first_name='Test',
            last_name='User'
        )

    def test_halaman_login_tidak_di_cache(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.has_header('Cache-Control'), 
            "Gagal! Tambahkan @never_cache pada fungsi halaman_login di views.py"
        )
        self.assertIn('max-age=0', response['Cache-Control'])
        self.assertIn('no-cache', response['Cache-Control'])

    def test_halaman_registrasi_tidak_di_cache(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header('Cache-Control'))
    
    def test_session_id_berubah_saat_login(self):
        """Mencegah Session Fixation dengan validasi pergantian ID"""
        self.client.session.save()
        session_lama = self.client.session.session_key
        
        response = self.client.post(reverse('accounts:login'), {
            'username': self.username,
            'password': self.password
        })
        
        session_baru = self.client.session.session_key
        self.assertNotEqual(session_lama, session_baru)
        self.assertRedirects(response, reverse('accounts:dashboard'))

    def test_logout_menghancurkan_session(self):
        self.client.force_login(self.user)
        self.assertIn('_auth_user_id', self.client.session)
        
        response = self.client.post(reverse('accounts:logout'))
        
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertRedirects(response, reverse('accounts:login'))

    def test_ganti_password_update_session_hash(self):
        self.client.force_login(self.user)
        
        response = self.client.post(reverse('accounts:ganti_password'), {
            'old_password': self.password,
            'new_password1': 'SandiBaru123!@#',
            'new_password2': 'SandiBaru123!@#',
        })
                
        self.assertIn('_auth_user_id', self.client.session)
        
        self.client.logout()
        response_login = self.client.post(reverse('accounts:login'), {
            'username': self.username,
            'password': 'SandiBaru123!@#'
        })
        self.assertRedirects(response_login, reverse('accounts:dashboard'))
    
    def test_brute_force_lockout(self):
        for _ in range(7):
            response = self.client.post(reverse('accounts:login'), {
                'username': self.username,
                'password': 'PasswordNgarang123'
            })
        
        self.assertTemplateUsed(response, 'accounts/lockout.html')
        self.assertTrue(AccessAttempt.objects.filter(username=self.username).exists())

    def test_pesan_error_login_ambigu(self):
        res1 = self.client.post(reverse('accounts:login'), {
            'username': 'user_ngaco_banget',
            'password': 'Password123!'
        })
        
        res2 = self.client.post(reverse('accounts:login'), {
            'username': self.username,
            'password': 'PasswordSalah123'
        })
        
        error1 = str(res1.context['form'].errors)
        error2 = str(res2.context['form'].errors)
        
        self.assertEqual(error1, error2, "Pesan error login tidak sama! Membocorkan informasi akun.")

    def test_password_di_database_adalah_hash(self):
        user_di_db = User.objects.get(username=self.username)
        
        self.assertNotEqual(
            user_di_db.password, 
            self.password, 
            "BAHAYA: Password tersimpan sebagai plaintext!"
        )
        
        self.assertTrue(
            user_di_db.password.startswith('pbkdf2_sha256$'),
            "Keamanan Kurang: Password tidak menggunakan hashing PBKDF2!"
        )

class CSRFLoginTest(TestCase):
    def setUp(self):
        self.client_csrf = Client(enforce_csrf_checks=True)
        self.nasabah = User.objects.create_user(
            username='budi_santoso',
            password='Rahasia@Bank1!',
            role='nasabah',
        )
        self.url = reverse('accounts:login')

    def test_login_tanpa_token_csrf_ditolak(self):
        """POST ke halaman login tanpa CSRF token harus ditolak (403)."""
        response = self.client_csrf.post(self.url, {
            'username': 'budi_santoso',
            'password': 'Rahasia@Bank1!',
        })
        self.assertEqual(response.status_code, 403)

    def test_login_method_get_tidak_perlu_csrf(self):
        """GET ke halaman login tidak memerlukan CSRF token."""
        response = self.client_csrf.get(self.url)
        self.assertNotEqual(response.status_code, 403)


class CSRFRegisterTest(TestCase):
    def setUp(self):
        self.client_csrf = Client(enforce_csrf_checks=True)
        self.url = reverse('accounts:register')

    def test_registrasi_tanpa_token_csrf_ditolak(self):
        """POST ke halaman registrasi tanpa CSRF token harus ditolak (403)."""
        response = self.client_csrf.post(self.url, {
            'username': 'siti_rahayu',
            'password1': 'Rahasia@Bank2!',
            'password2': 'Rahasia@Bank2!',
        })
        self.assertEqual(response.status_code, 403)

    def test_registrasi_method_get_tidak_perlu_csrf(self):
        """GET ke halaman registrasi tidak memerlukan CSRF token."""
        response = self.client_csrf.get(self.url)
        self.assertNotEqual(response.status_code, 403)


class CSRFGantiPasswordTest(TestCase):
    def setUp(self):
        self.client_csrf = Client(enforce_csrf_checks=True)
        self.nasabah = User.objects.create_user(
            username='andi_wijaya',
            password='Rahasia@Bank3!',
            role='nasabah',
        )
        self.url = reverse('accounts:ganti_password')

    def test_ganti_sandi_tanpa_token_csrf_ditolak(self):
        """POST ganti password tanpa CSRF token harus ditolak (403)."""
        self.client_csrf.force_login(self.nasabah)
        response = self.client_csrf.post(self.url, {
            'old_password': 'Rahasia@Bank3!',
            'new_password1': 'SandiKuat@Baru1!',
            'new_password2': 'SandiKuat@Baru1!',
        })
        self.assertEqual(response.status_code, 403)

    def test_ganti_sandi_method_get_tidak_perlu_csrf(self):
        """GET ke halaman ganti password tidak memerlukan CSRF token."""
        self.client_csrf.force_login(self.nasabah)
        response = self.client_csrf.get(self.url)
        self.assertNotEqual(response.status_code, 403)


class CSRFLogoutTest(TestCase):
    def setUp(self):
        self.client_csrf = Client(enforce_csrf_checks=True)
        self.nasabah = User.objects.create_user(
            username='dewi_kusuma',
            password='Rahasia@Bank4!',
            role='nasabah',
        )
        self.url = reverse('accounts:logout')

    def test_logout_tanpa_token_csrf_ditolak(self):
        """POST logout tanpa CSRF token harus ditolak (403)."""
        self.client_csrf.force_login(self.nasabah)
        response = self.client_csrf.post(self.url)
        self.assertEqual(response.status_code, 403)


class CSRFProfilTest(TestCase):
    def setUp(self):
        self.client_csrf = Client(enforce_csrf_checks=True)
        self.nasabah = User.objects.create_user(
            username='rini_hartono',
            password='Rahasia@Bank5!',
            role='nasabah',
        )
        self.url = reverse('accounts:profil')

    def test_edit_profil_tanpa_token_csrf_ditolak(self):
        """POST edit profil tanpa CSRF token harus ditolak (403)."""
        self.client_csrf.force_login(self.nasabah)
        response = self.client_csrf.post(self.url, {
            'first_name': 'Rini',
            'last_name': 'Hartono',
        })
        self.assertEqual(response.status_code, 403)

    def test_edit_profil_method_get_tidak_perlu_csrf(self):
        """GET ke halaman profil tidak memerlukan CSRF token."""
        self.client_csrf.force_login(self.nasabah)
        response = self.client_csrf.get(self.url)
        self.assertNotEqual(response.status_code, 403)


class CSRFTambahPenggunaTest(TestCase):
    def setUp(self):
        self.client_csrf = Client(enforce_csrf_checks=True)
        self.supervisor = User.objects.create_user(
            username='ahmad_fauzi',
            password='Rahasia@Bank6!',
            role='supervisor',
        )
        self.url = reverse('accounts:tambah_user')

    def test_tambah_pengguna_tanpa_token_csrf_ditolak(self):
        """POST tambah user tanpa CSRF token harus ditolak (403)."""
        self.client_csrf.force_login(self.supervisor)
        response = self.client_csrf.post(self.url, {
            'username': 'nasabah_baru',
            'password1': 'Rahasia@Bank7!',
            'password2': 'Rahasia@Bank7!',
            'role': 'nasabah',
        })
        self.assertEqual(response.status_code, 403)

    def test_tambah_pengguna_method_get_tidak_perlu_csrf(self):
        """GET ke halaman tambah user tidak memerlukan CSRF token."""
        self.client_csrf.force_login(self.supervisor)
        response = self.client_csrf.get(self.url)
        self.assertNotEqual(response.status_code, 403)


class CSRFTogglePenggunaTest(TestCase):
    def setUp(self):
        self.client_csrf = Client(enforce_csrf_checks=True)
        self.supervisor = User.objects.create_user(
            username='hendra_gunawan',
            password='Rahasia@Bank8!',
            role='supervisor',
        )
        self.nasabah_target = User.objects.create_user(
            username='maya_sari',
            password='Rahasia@Bank9!',
            role='nasabah',
        )
        self.url = reverse('accounts:toggle_aktif_user', args=[self.nasabah_target.pk])

    def test_toggle_pengguna_tanpa_token_csrf_ditolak(self):
        """POST toggle user tanpa CSRF token harus ditolak (403)."""
        self.client_csrf.force_login(self.supervisor)
        response = self.client_csrf.post(self.url)
        self.assertEqual(response.status_code, 403)

    def test_status_pengguna_tidak_berubah_tanpa_csrf(self):
        """Status aktif user tidak boleh berubah jika CSRF gagal."""
        self.client_csrf.force_login(self.supervisor)
        status_awal = self.nasabah_target.is_active
        self.client_csrf.post(self.url)
        self.nasabah_target.refresh_from_db()
        self.assertEqual(self.nasabah_target.is_active, status_awal)