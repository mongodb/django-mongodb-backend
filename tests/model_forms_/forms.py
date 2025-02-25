from django import forms

from .models import Author, Book


class AuthorForm(forms.ModelForm):
    class Meta:
        fields = "__all__"
        model = Author


class BookForm(forms.ModelForm):
    class Meta:
        fields = "__all__"
        model = Book
