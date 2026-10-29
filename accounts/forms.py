import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Users, ContributorApplication
from articles.models import Categories

class AdminUserEditForm(forms.ModelForm):
    class Meta:
        model = Users
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'bio',
            'role',
            'status_kontributor',
            'is_active',
        ]

        labels = {
            'username': 'Username',
            'email': 'Email',
            'first_name': 'Nama depan',
            'last_name': 'Nama belakang',
            'bio': 'Bio',
            'role': 'Peran pengguna',
            'status_kontributor': 'Status kontributor',
            'is_active': 'Akun aktif',
        }

        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            'role': forms.Select(attrs={
                'class': 'form-control',
            }),
            'status_kontributor': forms.Select(attrs={
                'class': 'form-control',
            }),
        }

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = Users
        fields = UserCreationForm.Meta.fields + ('email', 'profile_picture')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = ''
        self.fields['profile_picture'].required = False


class ContributorApplicationForm(forms.ModelForm):
    class Meta:
        model = ContributorApplication
        fields = [
            'nik',
            'full_name',
            'address',
            'occupation',
            'gender',
            'bio',
            'portfolio_link',
        ]

        labels = {
            'nik': 'NIK',
            'full_name': 'Nama lengkap',
            'address': 'Alamat lengkap',
            'occupation': 'Pekerjaan',
            'gender': 'Jenis kelamin',
            'bio': 'Bio penulis',
            'portfolio_link': 'Link portofolio',
        }

        widgets = {
            'nik': forms.TextInput(attrs={
                'placeholder': 'Masukkan 16 digit NIK',
                'inputmode': 'numeric',
                'maxlength': '16',
                'autocomplete': 'off',
                'required': True,
            }),
            'full_name': forms.TextInput(attrs={
                'placeholder': 'Masukkan nama lengkap',
                'autocomplete': 'name',
                'required': True,
            }),
            'address': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Masukkan alamat lengkap (opsional)',
            }),
            'occupation': forms.TextInput(attrs={
                'placeholder': 'Contoh: Pelajar, Mahasiswa, Karyawan',
            }),
            'gender': forms.Select(),
            'bio': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Ceritakan minat menulismu (opsional)',
            }),
            'portfolio_link': forms.URLInput(attrs={
                'placeholder': 'https://contoh.com/karya (opsional)',
            }),
        }

    def clean_nik(self):
        nik = self.cleaned_data.get('nik', '').strip()

        if not nik:
            raise forms.ValidationError('NIK wajib diisi.')

        if not re.fullmatch(r'\d{16}', nik):
            raise forms.ValidationError(
                'NIK harus terdiri dari tepat 16 digit angka.'
            )

        return nik

    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name', '').strip()

        if not full_name:
            raise forms.ValidationError('Nama lengkap wajib diisi.')

        return full_name

    def clean_portfolio_link(self):
        link = (self.cleaned_data.get('portfolio_link') or '').strip()

        if not link:
            return ''

        if not link.startswith(('http://', 'https://')):
            raise forms.ValidationError(
                'Link portofolio harus diawali http:// atau https://.'
            )

        return link


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Users
        fields = ['profile_picture', 'bio', 'banner_picture']
        widgets = {
            'bio': forms.TextInput(attrs={'placeholder': 'Ceritakan dirimu dalam satu kalimat...'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Categories
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Nama kategori, misal: Hot News'})
        }