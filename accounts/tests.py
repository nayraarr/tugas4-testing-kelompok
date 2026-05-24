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

    # ========================================================
    # 1. TEST MITIGASI CACHE (BACK-BUTTON ATTACK)
    # ========================================================
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

    # ========================================================
    # 2. TEST SESSION MANAGEMENT & FIXATION
    # ========================================================
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

    # ========================================================
    # 3. TEST GANTI PASSWORD (SESSION INVALIDATION)
    # ========================================================
    def test_ganti_password_update_session_hash(self):
        self.client.force_login(self.user)
        
        response = self.client.post(reverse('accounts:ganti_password'), {
            'old_password': self.password,
            'new_password1': 'SandiBaru123!@#',
            'new_password2': 'SandiBaru123!@#',
        })
                
        self.assertIn('_auth_user_id', self.client.session)
        
        # Uji login dari awal dengan password baru menggunakan sistem auth asli
        self.client.logout()
        response_login = self.client.post(reverse('accounts:login'), {
            'username': self.username,
            'password': 'SandiBaru123!@#'
        })
        self.assertRedirects(response_login, reverse('accounts:dashboard'))

    # ========================================================
    # 4. TEST BRUTE FORCE PROTECTION (DJANGO-AXES)
    # ========================================================
    def test_brute_force_lockout(self):
        for _ in range(7):
            response = self.client.post(reverse('accounts:login'), {
                'username': self.username,
                'password': 'PasswordNgarang123'
            })
        
        self.assertTemplateUsed(response, 'accounts/lockout.html')
        self.assertTrue(AccessAttempt.objects.filter(username=self.username).exists())