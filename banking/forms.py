from decimal import Decimal

from django import forms
from decimal import Decimal
from .models import Rekening, TopUp
from banking.validators import validate_safe_input, validate_nominal, validate_no_rekening

class TransferForm(forms.Form):
    rekening_tujuan = forms.CharField(
        max_length=10,
        validators=[validate_no_rekening],
        label='Nomor Rekening Tujuan',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10 digit nomor rekening'})
    )
    nominal = forms.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal('10000'),
        validators=[validate_nominal],
        label='Nominal Transfer',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Minimum Rp 10.000'})
    )
    keterangan = forms.CharField(
        max_length=200, required=False,
        validators=[validate_safe_input],
        label='Keterangan',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opsional'})
    )

    def __init__(self, *args, rekening_asal=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.rekening_asal = rekening_asal

    def clean_rekening_tujuan(self):
        nomor = self.cleaned_data['rekening_tujuan']
        if not nomor.isdigit() or len(nomor) != 10:
            raise forms.ValidationError('Nomor rekening harus 10 digit angka.')
        try:
            tujuan = Rekening.objects.get(nomor_rekening=nomor, aktif=True)
        except Rekening.DoesNotExist:
            raise forms.ValidationError('Rekening tujuan tidak ditemukan atau tidak aktif.')
        if self.rekening_asal and tujuan == self.rekening_asal:
            raise forms.ValidationError('Tidak dapat transfer ke rekening sendiri.')
        self.rekening_tujuan_obj = tujuan
        return nomor

    def clean_nominal(self):
        nominal = self.cleaned_data['nominal']
        if self.rekening_asal and nominal > self.rekening_asal.saldo:
            raise forms.ValidationError('Saldo tidak mencukupi.')
        return nominal

class MutasiFilterForm(forms.Form):
    PERIODE_CHOICES = [
        ('7',  '7 Hari Terakhir'),
        ('30', '30 Hari Terakhir'),
        ('90', '3 Bulan Terakhir'),
        ('all','Semua'),
    ]
    periode = forms.ChoiceField(
        choices=PERIODE_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    jenis = forms.ChoiceField(
        choices=[('', 'Semua Jenis'), ('transfer', 'Transfer'), ('topup', 'Top-up')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    
class TopUpForm(forms.Form):
    nominal = forms.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal('50000'),
        label='Nominal Top-up',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Minimum Rp 50.000'})
    )
    metode = forms.ChoiceField(
        choices=TopUp.METODE_CHOICES,
        label='Metode Top-up',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class ApprovalForm(forms.Form):
    keputusan = forms.ChoiceField(
        choices=[('approve', 'Setujui'), ('reject', 'Tolak')],
        widget=forms.RadioSelect
    )
    catatan = forms.CharField(
        max_length=300, required=False,
        validators=[validate_safe_input],
        label='Catatan',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Catatan opsional'})
    )
    
class TopUpForm(forms.Form):
    nominal = forms.DecimalField(
        max_digits=15, decimal_places=2, min_value=Decimal('50000'),
        label='Nominal Top-up',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Minimum Rp 50.000'})
    )
    metode = forms.ChoiceField(
        choices=TopUp.METODE_CHOICES,
        label='Metode Top-up',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
class MutasiFilterForm(forms.Form):
    PERIODE_CHOICES = [
        ('7',  '7 Hari Terakhir'),
        ('30', '30 Hari Terakhir'),
        ('90', '3 Bulan Terakhir'),
        ('all','Semua'),
    ]
    periode = forms.ChoiceField(
        choices=PERIODE_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    jenis = forms.ChoiceField(
        choices=[('', 'Semua Jenis'), ('transfer', 'Transfer'), ('topup', 'Top-up')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
