# Mobile Banking Application — PKPL 2026

**Kelompok:** PKPassword123! 

**Anggota:**
> | Nama | NPM |
> |------|-----|
> | Abigail Namaratonggi Pasaribu | 2406495773 |
> | Kanayra Maritza Sanika Adeeva | 2406437880 | 
> | Tsaniya Fini Ardiyanti | 2406437893 | 
> | Zhafira Uzma | 2406495451 | 
> | Zita Nayra Ardini | 2406404913 |

---

## 1. Deskripsi Aplikasi

### Skenario

Aplikasi Mobile Banking berbasis web yang memungkinkan nasabah melakukan transaksi keuangan secara digital. Aplikasi dibangun menggunakan Django dengan tiga layanan utama: Transfer Dana, Mutasi Rekening, dan Top-up Saldo.

### Fitur yang Diimplementasikan

- **Transfer Dana** — Nasabah dapat mentransfer saldo ke rekening lain. Transfer di bawah Rp 10.000.000 disetujui Teller; di atas nominal tersebut memerlukan persetujuan Supervisor.
- **Mutasi Rekening** — Nasabah dapat melihat riwayat transaksi masuk dan keluar pada rekeningnya.
- **Top-up Saldo** — Nasabah mengajukan top-up yang diproses dan disetujui oleh Teller.

### Role Pengguna

| Role | Akses |
|------|-------|
| Nasabah | Transfer, top-up, lihat mutasi & saldo sendiri |
| Teller | Proses top-up, approve transfer < Rp 10 juta |
| Supervisor | Approve transfer ≥ Rp 10 juta, kelola user, lihat laporan |

### Tech Stack

- **Backend:** Django 4.x (Python 3.11)
- **Database:** SQLite (development)
- **Frontend:** Bootstrap 5 + Django Templates
- **Security Libraries:** `django-axes`, `bleach`, `python-decouple`

---

## 2. Petunjuk Instalasi

```bash
# 1. Clone repo
git clone <URL_GITLAB_KELOMPOK>
cd mobilebanking

# 2. Buat virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Buat file .env di root project (sama dengan manage.py)
echo "SECRET_KEY=ganti-dengan-secret-key-acak-anda" > .env

# 5. Migrasi database
python manage.py migrate

# 6. Isi data dummy (user + rekening awal)
python manage.py shell < seed_data.py

# 7. Jalankan server
python manage.py runserver
# Buka http://127.0.0.1:8000
```

### Akun Login (Data Dummy)

| Username | Password | Role |
|----------|----------|------|
| supervisor1 | password123 | Supervisor |
| teller1 | password123 | Teller |
| nasabah1 | password123 | Nasabah (Rp 5.000.000) |
| nasabah2 | password123 | Nasabah (Rp 12.500.000) |

---

## 3. Implementasi Secure Coding

### 3.1 Code Injection Prevention

**Vulnerability yang Dimitigasi:** CWE-79 (XSS), CWE-94 (Code Injection), CWE-116 (Improper Output Encoding)

**Penjelasan:** Tanpa validasi, input pengguna yang berisi karakter berbahaya seperti `<script>`, `&`, atau `"` dapat dieksekusi sebagai kode di browser (XSS) atau diinterpretasikan sebagai markup HTML.

**Kode Vulnerable:**
```python
# banking/views.py — VULNERABLE
# Input langsung diambil dari POST tanpa validasi apapun
def transfer_view(request):
    if request.method == 'POST':
        keterangan = request.POST.get('keterangan')
        # <script>alert('XSS')</script> tersimpan langsung ke DB
        Transaksi.objects.create(
            ...
            keterangan=keterangan,
        )
```
<!-- Template — VULNERABLE -->
<!-- Jika |safe dipakai, script dieksekusi di browser -->
<td>{{ transaksi.keterangan|safe }}</td>


**Kode Secure:**
# banking/validators.py 
import re
from django.core.exceptions import ValidationError
# membuat fungsi validate safe input
def validate_safe_input(value):
    karakter_berbahaya = r'[<>&"\';(){}\|]'
    if re.search(karakter_berbahaya, value):
        raise ValidationError('Input mengandung karakter yang tidak diizinkan.')

# banking/forms.py — SECURE
# Validator dipasang langsung di field form
class TransferForm(forms.Form):
    keterangan = forms.CharField(
        validators=[validate_safe_input],  # ← tolak karakter berbahaya
        ...
    )

class ApprovalForm(forms.Form):
    catatan = forms.CharField(
        validators=[validate_safe_input],  # ← tolak karakter berbahaya
        ...
    )

# accounts/forms.py 
class RegisterNasabahForm(forms.ModelForm):
    def clean_first_name(self):
        value = self.cleaned_data.get('first_name', '')
        validate_safe_input(value)  # ← validasi nama depan
        return value

    def clean_last_name(self):
        value = self.cleaned_data.get('last_name', '')
        validate_safe_input(value)  # ← validasi nama belakang
        return value

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        validators=[validate_safe_input],  # ← tolak SQL/XSS di username
        ...
    )

# banking/views.py 
import bleach

# Di halaman_transfer
keterangan = bleach.clean(
    form.cleaned_data.get('keterangan', ''),
    tags=[], strip=True  # ← strip semua HTML tag
)
Transaksi.objects.create(..., keterangan=keterangan)

# Di _jalankan_verifikasi (proses topup & transfer)
catatan = bleach.clean(
    form.cleaned_data.get('catatan', ''),
    tags=[], strip=True  # ← strip semua HTML tag
)

<!-- Template — SECURE -->
<!-- Django auto-escape aktif, tidak ada |safe -->
<td>{{ transaksi.keterangan }}</td>

**Teknik Mitigasi:**
- `banking/validators.py` — fungsi `validate_safe_input()` menolak karakter `< > & " ' ; ( ) { } |` menggunakan regex blocklist sebelum data diproses lebih lanjut. Validator ini dipasang di semua field teks bebas — keterangan (TransferForm), catatan (ApprovalForm), username (LoginForm), serta first_name, last_name, alamat (RegisterNasabahForm & EditProfilForm). 

- Sanitasi Output `bleach.clean()`  field keterangan di halaman_transfer dan field catatan di _jalankan_verifikasi tetap dilewatkan bleach.clean(tags=[], strip=True) sebelum disimpan ke database. Bleach akan men-strip semua HTML tag yang tersisa ini sebagai lapisan kedua jika ada celah yang lolos dari validator

- Auto-escape Template Engine
Django Template Engine secara default meng-escape semua variabel {{ variabel }} — karakter < > & " ' dikonversi ke HTML entity sehingga tidak bisa dieksekusi browser. Seluruh template diverifikasi tidak ada |safe yang menonaktifkan escape ini, sehingga data yang ditampilkan ke user selalu aman meskipun tersimpan di database.

---

### 3.2 Broken Authentication Mitigation

**Vulnerability yang Dimitigasi:** CWE-256 ( Plaintext storage), CWE-916 (Password hash kuat), CWE-307 (Rate limiting), CWE-613 (Session expiration), CWE-306 (Least privilege), CWE-204 (Generic error message)

**Penjelasan:** Autentikasi yang lemah memungkinkan penyerang menebak password (brute force), mencuri session, atau mengakses fitur yang bukan haknya.

**Kode Vulnerable:**
# password plaintext, tidak ada rate limiting,
# pesan error membocorkan informasi
def login_view(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    try:
        user = User.objects.get(username=username)
        if user.password == password:  # ← plaintext compare!
            request.session['user_id'] = user.id
    except User.DoesNotExist:
        return "Username tidak ditemukan"  # ← bocorkan info username!
    # tidak ada rate limiting, brute force bebas

# semua endpoint bisa diakses semua role
def halaman_laporan(request):
    return render(request, 'banking/laporan.html')  # ← tidak ada cek role

**Kode Secure:**
# config/settings.py — SECURE

# Session management aman
SESSION_COOKIE_HTTPONLY = True        # ← JS tidak bisa akses cookie
SESSION_COOKIE_AGE = 1800             # ← expired 30 menit
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Rate limiting django-axes
AXES_FAILURE_LIMIT = 6               # ← lockout setelah 6x gagal
AXES_COOLOFF_TIME = 1                # ← cooloff 1 jam
AXES_LOCKOUT_TEMPLATE = 'accounts/lockout.html'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',  # ← intercept login
    'django.contrib.auth.backends.ModelBackend',
]

# accounts/forms.py
class LoginForm(AuthenticationForm):
    # Pesan error generik — tidak bocorkan info 
    error_messages = {
        'invalid_login': 'Username atau password yang Anda masukkan salah.',
        'inactive': 'Akun ini tidak aktif.',
    }

class RegisterNasabahForm(forms.ModelForm):
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])  # ← PBKDF2 hash
        user.role = 'nasabah'
        if commit:
            user.save()
        return user

# accounts/views.py
from django.contrib.auth import login, logout

@csrf_protect
def halaman_login(request):
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)  # ← session aman, PBKDF2 verified
        return redirect('accounts:dashboard')

@csrf_protect
def halaman_logout(request):
    if request.method == 'POST':
        logout(request)  # ← session dihapus di sisi server
    return redirect('accounts:login')

# accounts/permission.py, least privilege per role
khusus_nasabah    = registri_akses.buat_dekorator('nasabah')
khusus_teller     = registri_akses.buat_dekorator('teller')
khusus_supervisor = registri_akses.buat_dekorator('supervisor')
khusus_staf       = registri_akses.buat_dekorator_gabungan('teller', 'supervisor')

# Setiap endpoint diproteksi decorator sesuai role
@login_required
@csrf_protect
@khusus_supervisor   # ← hanya supervisor
def halaman_tambah_pengguna(request): ...

@login_required
@csrf_protect
@khusus_nasabah      # ← hanya nasabah
def halaman_transfer(request): ...


**Teknik Mitigasi:**
- Password Hashing (PBKDF2) -> Password di-hash menggunakan PBKDF2 via set_password() dari Django AbstractUser. Password tidak pernah disimpan plaintext di database maupun di kode, terbukti dari audit seluruh codebase tidak ada assignment 
user.password = plaintext.

- Rate Limiting (django-axes) -> AxesStandaloneBackend mencatat setiap percobaan login gagal. Akun dikunci setelah 6x gagal login dengan cooloff 1 jam — mencegah brute force attack. Halaman lockout ditampilkan via AXES_LOCKOUT_TEMPLATE.

- Session Management -> SESSION_COOKIE_HTTPONLY=True mencegah JavaScript mengakses session cookie. SESSION_COOKIE_AGE=1800 membatasi session 30 menit. SESSION_EXPIRE_AT_BROWSER_CLOSE=True menghapus session saat browser ditutup. logout() Django menghapus session di sisi server secara penuh, token lama tidak bisa digunakan kembali.

- Least Privilege per Role -> accounts/permission.py mengimplementasikan sistem dekorator berbasis role, khusus_nasabah, khusus_teller, khusus_supervisor, khusus_staf. Setiap endpoint diproteksi dekorator yang sesuai, role yang tidak berhak otomatis di-redirect ke dashboard dengan pesan error.

- Generic Error Message -> LoginForm.error_messages dikonfigurasi dengan pesan generik "Username atau password yang Anda masukkan salah", tidak membocorkan apakah username atau password yang salah, sehingga attacker tidak bisa menebak keberadaan akun.

---

### 3.3 CSRF Protection

**Vulnerability yang Dimitigasi:** CWE-352 (Cross-Site Request Forgery)

**Penjelasan:** Tanpa CSRF token, penyerang dapat membuat form di situs lain yang diam-diam mengirim request ke aplikasi atas nama pengguna yang sedang login.

**Kode Vulnerable:**
```html
<!-- Form tanpa CSRF token — bisa diserang dari situs manapun -->
<form method="POST" action="/banking/transfer/">
  <input name="nominal" type="number">
  <button>Transfer</button>
</form>
```
# settings.py — middleware tidak aktif
# CsrfViewMiddleware tidak ada, semua POST request diproses tanpa verifikasi
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # CsrfViewMiddleware tidak ada — semua POST request diproses tanpa verifikasi
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]

# views.py — tidak ada verifikasi CSRF
def transfer_view(request):
    if request.method == 'POST':
        # langsung proses tanpa cek token
        keterangan = request.POST.get('keterangan')
        Transaksi.objects.create(...)


**Kode Secure:**
```html
<!-- CSRF token memastikan request hanya dari form aplikasi sendiri -->
<form method="POST" action="/banking/transfer/">
  {% csrf_token %}
  <input name="nominal" type="number">
  <button>Transfer</button>
</form>
```

# config/settings.py — CsrfViewMiddleware aktif
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',     # ← CORS protection
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', # ← verifikasi token semua POST
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]

# CORS dikonfigurasi eksplisit
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

CORS_ALLOW_ALL_ORIGINS = False

# banking/views.py — @csrf_protect sebagai double protection
from django.views.decorators.csrf import csrf_protect

@login_required
@csrf_protect        # ← verifikasi ulang di level view
@khusus_nasabah
def halaman_transfer(request):
    if request.method == 'POST' and form.is_valid():
        ...

# accounts/views.py
@csrf_protect
def halaman_login(request):
    ...

**Teknik Mitigasi:**
- CsrfViewMiddleware di config/settings.py memverifikasi setiap request POST secara otomatis. Token yang tidak ada atau tidak cocok menyebabkan HTTP 403 Forbidden sebelum request sampai ke view manapun.
- `{% csrf_token %}` di semua 12 form POST (login, register, transfer, topup, proses, toggle, topup dll.)
- `@csrf_protect` sebagai double protection dipasang di 5 view banking/views.py dan 7 view accounts/views.py — memastikan verifikasi tetap berjalan meskipun middleware dinonaktifkan.
- CORS eksplisit (django-cors-headers) -> CORS_ALLOWED_ORIGINS dikonfigurasi hanya mengizinkan origin terdaftar. CORS_ALLOW_ALL_ORIGINS = False memastikan cross-origin request dari domain tidak terdaftar ditolak.

---

### 3.4 SQL Injection Prevention

**Vulnerability yang Dimitigasi:** CWE-89 (SQL Injection)

**Penjelasan:** Menggabungkan input pengguna langsung ke string SQL memungkinkan penyerang memanipulasi query untuk membaca, mengubah, atau menghapus data.

**Kode Vulnerable:**
# VULNERABLE — string concatenation langsung ke SQL
def cari_rekening(nomor):
    query = f"SELECT * FROM banking_rekening WHERE nomor_rekening = '{nomor}'"
    cursor.execute(query)
    # Payload: ' OR '1'='1 → ambil semua rekening

def login_view(request):
    username = request.POST.get('username')
    query = f"SELECT * FROM auth_user WHERE username = '{username}'"
    cursor.execute(query)
    # Payload: ' OR '1'='1' → bypass login

def cari_transaksi(keyword):
    query = "SELECT * FROM banking_transaksi WHERE keterangan = '" + keyword + "'"
    cursor.execute(query)
    # Payload: ' UNION SELECT username, password, null FROM auth_user --
    # → ekstrak data sensitif dari tabel lain

**Kode Secure:**
# banking/views.py seluruh query pakai Django ORM
from django.db.models import Q

# Filter transaksi, ORM otomatis parameterized query
class QueryRiwayat:
    def __init__(self, rekening):
        self._qs = Transaksi.objects.filter(
            Q(rekening_asal=rekening) | Q(rekening_tujuan=rekening)
        )

    def filter_rentang(self, periode):
        if periode and periode != 'all':
            batas = timezone.now() - timedelta(days=int(periode))
            self._qs = self._qs.filter(waktu__gte=batas)  # ← parameterized
        return self

    def filter_jenis(self, jenis):
        if jenis:
            self._qs = self._qs.filter(jenis=jenis)  # ← parameterized
        return self

# banking/operasi.py — SECURE — transaction.atomic + select_for_update
from django.db import transaction

@transaction.atomic
def jalankan_transfer(transaksi, petugas, disetujui, catatan=''):
    # select_for_update() — lock row, cegah race condition
    transaksi = Transaksi.objects.select_for_update().get(pk=transaksi.pk)
    asal      = Rekening.objects.select_for_update().get(pk=transaksi.rekening_asal.pk)
    tujuan    = Rekening.objects.select_for_update().get(pk=transaksi.rekening_tujuan.pk)
    ...

@transaction.atomic
def jalankan_topup(topup, petugas, disetujui, catatan=''):
    topup    = TopUp.objects.select_for_update().get(pk=topup.pk)
    rekening = Rekening.objects.select_for_update().get(pk=topup.rekening.pk)
    ...

# banking/forms.py — SECURE — validasi format sebelum query
class TransferForm(forms.Form):
    rekening_tujuan = forms.CharField(
        validators=[validate_no_rekening],  # ← hanya 10 digit angka
    )
    nominal = forms.DecimalField(
        validators=[validate_nominal],      # ← hanya angka positif
    )

# banking/validators.py
def validate_no_rekening(value):
    if not value.isdigit():
        raise ValidationError('Nomor rekening hanya boleh berisi angka.')
    if len(value) != 10:
        raise ValidationError('Nomor rekening harus tepat 10 digit.')

# banking/views.py — SECURE — authorization check per user
@login_required
@khusus_nasabah
def halaman_mutasi(request):
    # Nasabah hanya bisa lihat rekening milik sendiri
    rekening = Rekening.objects.get(pemilik=request.user)  # ← filter by user
    ...

@login_required
@khusus_supervisor
def halaman_kelola_rekening(request):
    q = request.GET.get('q', '')
    qs = Rekening.objects.select_related('pemilik').all()
    if q:
        # Pencarian pakai ORM Q() — bukan string concatenation
        qs = qs.filter(
            Q(nomor_rekening__icontains=q)
            | Q(pemilik__first_name__icontains=q)
            | Q(pemilik__last_name__icontains=q)
            | Q(pemilik__username__icontains=q)
        )

**Teknik Mitigasi:**
- Parameterized Query -> Seluruh operasi database menggunakan Django ORM — tidak ada satu pun cursor.execute() dengan string concatenation di codebase. Django ORM secara otomatis menghasilkan parameterized query yang memisahkan kode SQL dari data, sehingga input user tidak pernah bisa diinterpretasikan sebagai perintah SQL. 
- Fungsi jalankan_transfer() dan jalankan_topup() dibungkus @transaction.atomic dengan select_for_update(), memastikan operasi debit-kredit berjalan atomik dan tidak terjadi race condition jika ada request bersamaan.
- validate_no_rekening() memastikan nomor rekening hanya boleh 10 digit angka sebelum digunakan sebagai parameter query. validate_nominal() memastikan nominal hanya angka positif. Payload seperti 1234567890' OR '1'='1' ditolak di level form sebelum menyentuh database.
- Setiap view hanya mengakses data milik request.user sendiri, nasabah tidak bisa mengakses rekening orang lain karena query selalu difilter pemilik=request.user. Endpoint pencarian di halaman_kelola_rekening menggunakan Q() ORM , bukan string concatenation.
- Aplikasi menggunakan SQLite sebagai database development. Pada SQLite tidak terdapat sistem user/role database seperti PostgreSQL, namun prinsip least privilege diterapkan di level aplikasi melalui decorator @khusus_nasabah, @khusus_teller, @khusus_supervisor

---

## 4. Screenshot Aplikasi

> Ganti jd screenshot dari aplikasi.

### Antarmuka Utama

| Halaman | Screenshot |
|---------|-----------|
| Dashboard Nasabah | *(screenshot)* |
| Halaman Transfer | *(screenshot)* |
| Mutasi Rekening | *(screenshot)* |
| Dashboard Teller (Antrian) | *(screenshot)* |

### Fitur Keamanan

| Fitur | Screenshot |
|-------|-----------|
| Halaman Lockout (django-axes) | *(screenshot)* |
| 403 Forbidden (CSRF attack) | *(screenshot)* |
| Password hash di admin | *(screenshot)* |
| Error validasi XSS input | *(screenshot)* |

---

## 5. Hasil Test Case

| TC# | Skenario | Expected | Actual | Status | Screenshot |
|-----|----------|----------|--------|--------| ---------- |
| TC-01 | Input `<script>alert('XSS')</script>` di field keterangan transfer | Error validasi, tidak tersimpan | *(isi)* | PASS/FAIL |
| TC-02 | Input `<b>bold</b>` di field nama | Tampil sebagai teks biasa | *(isi)* | PASS/FAIL |
| TC-03 | Login salah 5x berturut-turut | Halaman lockout muncul | Halaman lockout muncul dengan pesan "Akun Sementara Terkunci, coba lagi dalam 1 jam" | PASS | ![alt text](screenshots/image.png) |
| TC-04 | Cek kolom password di Django Admin | Hash `pbkdf2_sha256$...` | Kolom password menampilkan pbkdf2_sha256$600000$<salt>$<hash>, bukan plaintext | PASS | ![alt text](screenshots/image2.png) |
| TC-05 | Logout → tekan Back browser | Redirect ke login | Browser redirect ke halaman login, tidak bisa kembali ke dashboard | PASS | ![alt text](screenshots/image3.png) | 
| TC-06 | View Page Source form transfer | `csrfmiddlewaretoken` ada di HTML | *(isi)* | PASS/FAIL |
| TC-07 | CSRF attack dari file HTML eksternal | 403 Forbidden | *(isi)* | PASS/FAIL |
| TC-08 | Input `' OR '1'='1` di field username | Pesan error login | *(isi)* | PASS/FAIL |
| TC-09 | Input `1; DROP TABLE banking_rekening;--` di keterangan | Error validasi | *(isi)* | PASS/FAIL |
| TC-10 | Nasabah akses `/laporan/` (supervisor only) | 403 Forbidden | *(isi)* | PASS/FAIL |.

---

## 6. Video Demo

🎬 **Link Video:** [YouTube](<URL_VIDEO>)

**Durasi:** 10–15 menit

**Isi Video:**
1. Demo aplikasi secara fungsional (maks. 2 menit) — login sebagai nasabah, transfer, mutasi, logout
2. Demonstrasi test case TC-01 s/d TC-10 beserta hasilnya
3. Penjelasan teknik mitigasi masing-masing komponen dan alasan pemilihan pendekatan tersebut

