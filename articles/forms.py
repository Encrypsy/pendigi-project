from django import forms
from .models import Articles
from articles.models import Categories

class CategoryChoices(forms.ChoiceField):
    data_category = Categories.objects.all()
    for category in data_category:
        category.name

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