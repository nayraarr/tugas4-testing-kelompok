from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('nasabah', 'Nasabah'),
        ('teller', 'Teller'),
        ('supervisor', 'Supervisor Bank'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='nasabah')
    no_telp = models.CharField(max_length=15, blank=True)
    alamat = models.TextField(blank=True)
    tanggal_lahir = models.DateField(null=True, blank=True)
    foto_profil = models.ImageField(upload_to='profil/', null=True, blank=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_nasabah(self):
        return self.role == 'nasabah'

    @property
    def is_teller(self):
        return self.role == 'teller'

    @property
    def is_supervisor(self):
        return self.role == 'supervisor'
