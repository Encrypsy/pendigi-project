from django import forms
from .models import PersonalNotes


class PersonalNoteForm(forms.ModelForm):
    class Meta:
        model = PersonalNotes
        fields = ['note_content']
        widgets = {
            'note_content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Insight apa yang kamu dapat dari artikel ini?'})
        }