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
        fields = ['bio', 'portfolio_link']
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Ceritakan latar belakang menulis kamu...'
            }),
            'portfolio_link': forms.TextInput(attrs={
                'placeholder': 'Link contoh tulisan (Medium, blog, dll)'
            }),
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Users
        fields = ['profile_picture', 'bio']
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