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

**Vulnerability yang Dimitigasi:** CWE-287 (Improper Authentication), CWE-307 (Brute Force), CWE-522 (Insufficiently Protected Credentials), CWE-384 (Session Fixation)

**Penjelasan:** Autentikasi yang lemah memungkinkan penyerang menebak password (brute force), mencuri session, atau mengakses fitur yang bukan haknya.

**Kode Vulnerable:**
```python
# Password plaintext, tidak ada rate limit
def login(request):
    user = User.objects.get(username=request.POST['username'])
    if user.password == request.POST['password']:   # plaintext!
        request.session['user_id'] = user.id
```

**Kode Secure:**
```python
from django.contrib.auth import authenticate, login

def login_view(request):
    form = LoginForm(request, data=request.POST)
    if form.is_valid():
        user = form.get_user()   # django-axes catat gagal login otomatis
        login(request, user)     # password PBKDF2, session aman
```

**Teknik Mitigasi:**
- Password hashing PBKDF2 via `AbstractUser` — tidak pernah simpan plaintext
- `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_AGE=1800`, `SESSION_EXPIRE_AT_BROWSER_CLOSE=True`
- `django-axes`: lockout setelah 5x gagal login, cooloff 1 jam
- Decorator `@nasabah_only`, `@teller_only`, `@supervisor_only` — least privilege enforcement

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

