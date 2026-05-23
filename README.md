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
[TODO]

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