from django import forms
from .models import Comments, Ratings


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comments
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tulis komentar...'})
        }


class RatingForm(forms.ModelForm):
    rating_value = forms.ChoiceField(
        choices=[(i, i) for i in range(1, 6)],
        widget=forms.RadioSelect(),
    )

    class Meta:
        model = Ratings
        fields = ['rating_value']