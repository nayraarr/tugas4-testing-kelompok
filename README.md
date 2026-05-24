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

## 1. Laporan Unit Testing

### Metodologi
Unit testing dilakukan menggunakan Django Test Framework dengan pendekatan black-box 
dan white-box testing. Setiap fungsi keamanan diuji secara terisolasi menggunakan 
test database sementara yang dibuat otomatis oleh Django.

**Tools yang digunakan:**
- Django Test Framework (unittest)
- Coverage.py untuk mengukur cakupan kode

**Cara menjalankan:**
```bash
coverage run manage.py test
coverage report
```

### Hasil Coverage

| Module | Statements | Miss | Coverage |
|--------|-----------|------|----------|
| banking/validators.py | 16 | 0 | 100% |
| banking/tests.py | 348 | 9 | 97% |
| banking/views.py | 217 | 66 | 70% |
| banking/forms.py | 46 | 5 | 89% |
| accounts/tests.py | 132 | 0 | 100% |
| accounts/views.py | 143 | 49 | 66% |
| **TOTAL** | **1313** | **255** | **81%** |

### Ringkasan Hasil Test

| Komponen | Jumlah Test | Passed | Failed |
|----------|------------|--------|--------|
| Code Injection Prevention | 16 | 16 | 0 |
| Broken Authentication | 6 | 6 | 0 |
| CSRF Protection | 18 | 18 | 0 |
| SQL Injection Prevention | 15 | 15 | 0 |
| **Total** | **56** | **56** | **0** |

---

### Detail Unit Test: Code Injection Prevention

**Fungsi yang diuji:** `validate_safe_input()`, `validate_nominal()`, 
`validate_no_rekening()`, `bleach.clean()`

#### TC-CI-01: Script Tag Injection (XSS)

| Test | Input | Expected | Status |
|------|-------|----------|--------|
| test_tolak_script_tag | `<script>alert('XSS')</script>` | ValidationError | ✅ PASS |
| test_tolak_script_tag_reflected | `<script src='evil.js'></script>` | ValidationError | ✅ PASS |
| test_bleach_strip_script_tag | `<script>alert('XSS')</script>` | Tag ter-strip | ✅ PASS |

#### TC-CI-02: HTML Injection

| Test | Input | Expected | Status |
|------|-------|----------|--------|
| test_tolak_html_injection_h1 | `<h1>Hacked</h1>` | ValidationError | ✅ PASS |
| test_tolak_html_injection_img_onerror | `<img src=x onerror=alert(1)>` | ValidationError | ✅ PASS |
| test_bleach_strip_html_tag | `<h1>Hacked</h1>` | Tampil sebagai teks | ✅ PASS |
| test_bleach_strip_img_onerror | `<img src=x onerror=alert(1)>` | Tag ter-strip | ✅ PASS |

#### TC-CI-03: Template Injection (SSTI)

| Test | Input | Expected | Status |
|------|-------|----------|--------|
| test_tolak_template_injection_kalkulasi | `{{7*7}}` | ValidationError | ✅ PASS |
| test_tolak_template_injection_secret_key | `{{config.SECRET_KEY}}` | ValidationError | ✅ PASS |

#### TC-CI-04c: Keterangan Transfer (Banking)

| Test | Input | Expected | Status |
|------|-------|----------|--------|
| test_keterangan_xss_ditolak_validator | `<script>alert('transfer intercepted')</script>` | Transaksi tidak terbuat | ✅ PASS |

#### Input Valid (Harus Lolos)

| Test | Input | Expected | Status |
|------|-------|----------|--------|
| test_terima_input_normal | `Bayar makan siang` | Lolos validasi | ✅ PASS |
| test_terima_input_angka | `Transfer 500000` | Lolos validasi | ✅ PASS |
| test_bleach_teks_normal_tidak_berubah | `Bayar makan siang` | Tidak berubah | ✅ PASS |

#### Karakter Berbahaya Lainnya

| Test | Input | Expected | Status |
|------|-------|----------|--------|
| test_tolak_karakter_ampersand | `test & inject` | ValidationError | ✅ PASS |
| test_tolak_karakter_semicolon | `test; DROP TABLE` | ValidationError | ✅ PASS |
| test_tolak_karakter_single_quote | `' OR '1'='1` | ValidationError | ✅ PASS |

---

## 2. Laporan Pentesting

### 1. Passive & Active Reconnaissance [TODO]
- Tools: nmap, OWASP ZAP
- Temuan: [port, endpoint, teknologi]
- Screenshot: [TODO]

### 2. Threat Modeling [TODO]
- Aset yang diidentifikasi: ...
- Tabel STRIDE: ...
- Prioritas ancaman: ...

### 3. Scanning & Enumeration [TODO]
| No | Vulnerability | Endpoint | Severity | Tool |
|----|--------------|----------|----------|------|
| 1  | XSS          | /search/ | Medium   | ZAP  |

### 4. Exploitation & Testing [TODO]
[Untuk setiap temuan: langkah, hasil, screenshot]

### 5. Remediation [TODO]
| Vulnerability | Status | Mitigasi yang sudah ada |
|--------------|--------|------------------------|
| SQL Injection | Protected | Django ORM |
| XSS | Protected | Django auto-escape |
| CSRF | Protected | {% csrf_token %} |