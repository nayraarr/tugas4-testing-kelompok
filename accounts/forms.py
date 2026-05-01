from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser

class RegisterNasabahForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    password2 = forms.CharField(
        label='Konfirmasi Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Konfirmasi Password'})
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'no_telp', 'alamat', 'tanggal_lahir']
        widgets = {
            'username':      forms.TextInput(attrs={'class': 'form-control'}),
            'first_name':    forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':     forms.TextInput(attrs={'class': 'form-control'}),
            'email':         forms.EmailInput(attrs={'class': 'form-control'}),
            'no_telp':       forms.TextInput(attrs={'class': 'form-control'}),
            'alamat':        forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tanggal_lahir': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get('password1'), cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Password tidak cocok.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.role = 'nasabah'
        if commit:
            user.save()
        return user
    
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )