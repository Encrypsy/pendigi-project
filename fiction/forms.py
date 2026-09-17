from django import forms
from .models import Stories, Chapters


class StoryForm(forms.ModelForm):
    class Meta:
        model = Stories
        fields = ['title', 'cover', 'description', 'genre', 'tags', 'target_pembaca']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Ceritakan sinopsis singkat ceritamu...'}),
            'genre': forms.RadioSelect(),
            'target_pembaca': forms.RadioSelect(),
            'tags': forms.TextInput(attrs={'placeholder': 'misal: percintaan sekolah remaja'}),
        }


class ChapterForm(forms.ModelForm):
    class Meta:
        model = Chapters
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Judul bab'}),
            'content': forms.Textarea(attrs={'id': 'id_content_raw', 'class': 'hidden-raw-content'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].required = False