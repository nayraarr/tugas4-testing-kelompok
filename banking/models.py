from decimal import Decimal

from django.db import models

from config import settings

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

