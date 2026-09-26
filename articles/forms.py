from django import forms
from .models import Articles, Banner
from articles.models import Categories

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Categories
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Nama kategori, misal: Hot News'})
        }


class ArticleUploadForm(forms.ModelForm):
    class Meta:
        model = Articles
        fields = ['title', 'thumbnail', 'category', 'content']
        widgets = {
            'category': forms.RadioSelect(),
            'content': forms.Textarea(attrs={'placeholder': 'Tulis isi artikel kamu di sini...'}),
        }

class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = ['title', 'description', 'type', 'image', 'link_url', 'order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Judul banner (opsional)'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Deskripsi singkat (opsional)'}),
            'link_url': forms.TextInput(attrs={'placeholder': '/articles/5/ atau https://...'}),
        }