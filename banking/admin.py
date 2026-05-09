from django.contrib import admin
from .models import Rekening, Transaksi, TopUp, Notifikasi


@admin.register(Rekening)
class RekeningAdmin(admin.ModelAdmin):
    list_display = ['nomor_rekening', 'pemilik', 'saldo', 'aktif', 'dibuat_pada']
    list_filter = ['aktif']
    search_fields = ['nomor_rekening', 'pemilik__username']


@admin.register(Transaksi)
class TransaksiAdmin(admin.ModelAdmin):
    list_display = ['id', 'jenis', 'nominal', 'rekening_asal', 'rekening_tujuan', 'status', 'waktu']
    list_filter = ['jenis', 'status']
    search_fields = ['rekening_asal__nomor_rekening', 'rekening_tujuan__nomor_rekening']


@admin.register(TopUp)
class TopUpAdmin(admin.ModelAdmin):
    list_display = ['id', 'rekening', 'nominal', 'metode', 'status', 'diproses_oleh', 'waktu_request']
    list_filter = ['status', 'metode']


@admin.register(Notifikasi)
class NotifikasiAdmin(admin.ModelAdmin):
    list_display = ['user', 'pesan', 'dibaca', 'waktu']
    list_filter = ['dibaca']
