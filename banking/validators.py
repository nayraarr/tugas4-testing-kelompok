import re
from django.core.exceptions import ValidationError

def validate_safe_input(value):
    """escape XSS/injection."""
    karakter_berbahaya = r'[<>&"\';(){}\|]'
    if re.search(karakter_berbahaya, value):
        raise ValidationError('Input mengandung karakter yang tidak diizinkan.')

def validate_nominal(value):
    if value <= 0:
        raise ValidationError('Nominal harus lebih dari 0.')
    if value > 1_000_000_000:
        raise ValidationError('Nominal melebihi batas maksimum.')

def validate_no_rekening(value):
    if not value.isdigit():
        raise ValidationError('Nomor rekening hanya boleh berisi angka.')
    if len(value) != 10:
        raise ValidationError('Nomor rekening harus tepat 10 digit.')