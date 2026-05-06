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
# Tidak ada validasi, input langsung disimpan ke DB
keterangan = request.POST.get('keterangan')
Transaksi.objects.create(..., keterangan=keterangan)
```

**Kode Secure:**
```python
import bleach
from banking.validators import validate_safe_input

# Sanitasi dengan bleach sebelum disimpan
keterangan = bleach.clean(
    form.cleaned_data.get('keterangan', ''),
    tags=[], strip=True
)
Transaksi.objects.create(..., keterangan=keterangan)
```

**Teknik Mitigasi:**
- `banking/validators.py` — fungsi `validate_safe_input()` menolak karakter `< > & " ' ; ( ) { } |`
- `bleach.clean()` di view untuk sanitasi HTML yang lolos validasi form
- Auto-escape Django Template Engine aktif — tidak ada `|safe` di template

---

### 3.2 Broken Authentication Mitigation

**Vulnerability yang Dimitigasi:** : CWE-256 (Plaintext Storage of Password), CWE-307 (Brute Force), CWE-613 (Insufficient Session Expiration), CWE-306 (Missing Authentication for Critical Function), CWE-204 (Observable Response Discrepancy)

**Penjelasan:** Autentikasi yang lemah memungkinkan penyerang menebak password (brute force), mencuri/menyalahgunakan session, mengakses endpoint tanpa login, atau melakukan enumerasi akun melalui pesan error yang berbeda.

**Kode Vulnerable:**
```python
# Password disimpan plaintext, tidak ada rate limit, tidak ada session management
def login(request):
    user = User.objects.get(username=request.POST['username'])
    if user.password == request.POST['password']:   # plaintext!
        request.session['user_id'] = user.id        # session fixation

# Tidak ada proteksi endpoint — siapa saja bisa akses
def halaman_admin(request):
    return render(request, 'admin.html')
```

**Kode Secure:**
```python
# accounts/forms.py — Pesan error ambigu mencegah enumerasi akun (CWE-204)
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        validators=[validate_safe_input],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    error_messages = {
        'invalid_login': 'Username atau password yang Anda masukkan salah.',
        'inactive': 'Akun ini tidak aktif.',
    }

# accounts/views.py — @never_cache + @csrf_protect, session dibuat ulang saat login
@csrf_protect
@never_cache
def halaman_login(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and _proses_login(request, form):
        return redirect('accounts:dashboard')
    return render(request, 'accounts/login.html', {'form': form})

# accounts/views.py — Proteksi endpoint dengan @login_required + @khusus_supervisor
@login_required
@khusus_supervisor
def halaman_kelola_pengguna(request):
    ...

# accounts/views.py — Dashboard dispatch berdasarkan role (least privilege)
_PETA_RENDERER = {
    'nasabah':    _render_dasbor_nasabah,
    'teller':     _render_dasbor_teller,
    'supervisor': _render_dasbor_supervisor,
}

@never_cache
@login_required
def halaman_beranda(request):
    peran = request.user.role
    renderer = _PETA_RENDERER.get(peran)
    if renderer is None:
        return redirect('accounts:login')
    return renderer(request)

# settings.py — Konfigurasi session dan django-axes
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 1800                  # 30 menit
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

AXES_FAILURE_LIMIT = 6                     # lockout setelah 5 gagal (ke-6 trigger)
AXES_COOLOFF_TIME = 1                      # cooloff 1 jam
AXES_LOCKOUT_TEMPLATE = 'accounts/lockout.html'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]
```

**Teknik Mitigasi:**
| Ancaman | Teknik Mitigasi |
|---------|----------------|
| Password plaintext | `AbstractUser` menggunakan PBKDF2-SHA256 secara otomatis via `set_password()` — tidak pernah simpan plaintext |
| Brute force | `django-axes`: lockout setelah >5 kali gagal, cooloff 1 jam | 
| Session fixation | `login()` Django otomatis rotate session ID setiap autentikasi berhasil |
| Session tidak kadaluarsa | `SESSION_COOKIE_AGE=1800`, `SESSION_EXPIRE_AT_BROWSER_CLOSE=True`, `@never_cache` pada dashboard & login |
| Akses tanpa autentikasi | `@login_required` pada semua view terproteksi; redirect ke `/accounts/login/` jika belum login | 
| Enumerasi akun | Pesan error identik untuk username salah maupun password salah pada `LoginForm.error_messages` |
| Least privilege | Decorator `@khusus_supervisor` + dispatch via `_PETA_RENDERER` — setiap role hanya dapat mengakses endpoint yang sesuai |
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

**Kode Secure:**
```html
<!-- CSRF token memastikan request hanya dari form aplikasi sendiri -->
<form method="POST" action="/banking/transfer/">
  {% csrf_token %}
  <input name="nominal" type="number">
  <button>Transfer</button>
</form>
```

**Teknik Mitigasi:**
- `CsrfViewMiddleware` aktif di `MIDDLEWARE` — tidak dihapus atau di-disable
- `{% csrf_token %}` di semua 11 form POST (login, register, transfer, topup, proses, toggle, dll.)
- `@csrf_protect` sebagai double protection di `transfer_view`, `topup_view`, `proses_topup_view`, `proses_transfer_view`
- Tidak ada `@csrf_exempt` di seluruh codebase

---

### 3.4 SQL Injection Prevention

**Vulnerability yang Dimitigasi:** CWE-89 (SQL Injection), CWE-20 (Improper Input Validation), CWE-285 (Improper Authorization)

**Penjelasan:** Menggabungkan input pengguna langsung ke string SQL memungkinkan penyerang memanipulasi query untuk membaca, mengubah, atau menghapus data.

**Kode Vulnerable:**
```python
def cari_rekening(nomor):
    query = f"SELECT * FROM banking_rekening WHERE nomor_rekening = '{nomor}'"
    cursor.execute(query)
    # Payload: ' OR '1'='1 → ambil semua rekening!
```

**Kode Secure:**
```python
def cari_rekening(nomor):
    # Django ORM — query otomatis terparameterisasi
    return Rekening.objects.get(nomor_rekening=nomor, aktif=True)
```

**Teknik Mitigasi:**
- Seluruh query menggunakan Django ORM — tidak ada `cursor.execute()` dengan string concatenation
- `@transaction.atomic` di `services.py` — transfer tidak setengah jalan jika terjadi error
- Setiap view hanya akses data milik `request.user` sendiri (authorization check)
- Hasil audit: `grep -rn "cursor.execute" .` → **0 hasil** di codebase

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
| TC-BA-01 | Password Hashing Verification | Kolom password menampilkan hash `pbkdf2_sha256$...` — bukan plaintext | Kolom password menampilkan `pbkdf2_sha256$600000$<salt>$<hash>`, bukan plaintext | PASS | ![TC-BA-01](screenshots/image2.png) |
| TC-BA-02 | Brute Force / Rate Limiting | Sistem menampilkan pesan "Akun dikunci sementara" / rate limit aktif; login tidak dapat dilanjutkan | Halaman lockout muncul dengan pesan "Akun Sementara Terkunci, coba lagi dalam 1 jam" | PASS | ![TC-BA-02](screenshots/image.png) |
| TC-BA-03 | Session Token Invalidation setelah Logout | Server merespons dengan redirect ke halaman login (HTTP 302) atau HTTP 401; TIDAK ada akses ke halaman terproteksi | Browser redirect ke halaman login, tidak bisa kembali ke dashboard dengan session lama | PASS | ![TC-BA-03](screenshots/image3.png) |
| TC-BA-04 | Akses Halaman Terproteksi Tanpa Login | Redirect ke halaman login; TIDAK ada konten halaman yang terproteksi yang ditampilkan |  Aplikasi melakukan redirect ke `/accounts/login/` dan menampilkan halaman login | PASS | ![TC-BA-03](screenshots/image4.png) |
| TC-BA-05 | Informasi Error yang Tidak Informatif | Kedua skenario menampilkan pesan yang SAMA — tidak membedakan "username tidak ditemukan" vs "password salah" |  Kedua skenario menampilkan pesan `"Username atau password yang Anda masukkan salah."` | PASS | ![TC-BA-05](screenshots/image5.png)|
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

