from django.db import models
from django.conf import settings
from decimal import Decimal


class Rekening(models.Model):
    nomor_rekening = models.CharField(max_length=10, unique=True)
    pemilik = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rekening')
    saldo = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    aktif = models.BooleanField(default=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diperbarui_pada = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nomor_rekening} - {self.pemilik.get_full_name()}"

    def saldo_formatted(self):
        return f"Rp {self.saldo:,.0f}"


class Transaksi(models.Model):
    JENIS_CHOICES = [('transfer', 'Transfer Dana'), ('topup', 'Top-up')]
    STATUS_CHOICES = [
        ('pending',  'Menunggu Persetujuan'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
    ]

    rekening_asal    = models.ForeignKey(Rekening, on_delete=models.PROTECT, related_name='transaksi_keluar', null=True, blank=True)
    rekening_tujuan  = models.ForeignKey(Rekening, on_delete=models.PROTECT, related_name='transaksi_masuk', null=True, blank=True)
    jenis            = models.CharField(max_length=10, choices=JENIS_CHOICES)
    nominal          = models.DecimalField(max_digits=15, decimal_places=2)
    keterangan       = models.TextField(blank=True)
    status           = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    waktu            = models.DateTimeField(auto_now_add=True)
    diproses_oleh    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='transaksi_diproses'
    )
    waktu_diproses   = models.DateTimeField(null=True, blank=True)
    catatan_staff    = models.TextField(blank=True)

    class Meta:
        ordering = ['-waktu']

    def __str__(self):
        return f"[{self.get_jenis_display()}] {self.nominal:,.0f} - {self.get_status_display()}"

    def nominal_formatted(self):
        return f"Rp {self.nominal:,.0f}"

    @property
    def butuh_supervisor(self):
        return self.jenis == 'transfer' and self.nominal >= 10_000_000


class TopUp(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Menunggu Proses'),
        ('selesai',  'Selesai'),
        ('ditolak',  'Ditolak'),
    ]
    METODE_CHOICES = [
        ('tunai',      'Tunai'),
        ('transfer',   'Transfer Bank Lain'),
        ('virtual',    'Virtual Account'),
    ]

    rekening        = models.ForeignKey(Rekening, on_delete=models.PROTECT, related_name='topup_set')
    nominal         = models.DecimalField(max_digits=15, decimal_places=2)
    metode          = models.CharField(max_length=10, choices=METODE_CHOICES, default='tunai')
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    waktu_request   = models.DateTimeField(auto_now_add=True)
    diproses_oleh   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='topup_diproses'
    )
    waktu_proses    = models.DateTimeField(null=True, blank=True)
    keterangan      = models.TextField(blank=True)

    class Meta:
        ordering = ['-waktu_request']

    def __str__(self):
        return f"TopUp {self.rekening.nomor_rekening} - Rp {self.nominal:,.0f} [{self.get_status_display()}]"

    def nominal_formatted(self):
        return f"Rp {self.nominal:,.0f}"


class Notifikasi(models.Model):
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifikasi')
    pesan     = models.TextField()
    dibaca    = models.BooleanField(default=False)
    waktu     = models.DateTimeField(auto_now_add=True)
    link      = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-waktu']

    def __str__(self):
        return f"Notif [{self.user.username}]: {self.pesan[:40]}"
