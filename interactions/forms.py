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
    rating_value = forms.TypedChoiceField(
        choices=[
            (1, '1 bintang'),
            (2, '2 bintang'),
            (3, '3 bintang'),
            (4, '4 bintang'),
            (5, '5 bintang'),
        ],
        coerce=float,
        widget=forms.RadioSelect(),
    )

    class Meta:
        model = Ratings
        fields = ['rating_value']