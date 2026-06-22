from django import forms

from .models import Author, Book, Movie, Retailer, Store


class AuthorForm(forms.ModelForm):
    class Meta:
        fields = "__all__"
        model = Author


class BookForm(forms.ModelForm):
    class Meta:
        fields = "__all__"
        model = Book


class MovieForm(forms.ModelForm):
    class Meta:
        fields = "__all__"
        model = Movie


class StoreForm(forms.ModelForm):
    class Meta:
        fields = "__all__"
        model = Store


class RetailerForm(forms.ModelForm):
    class Meta:
        fields = "__all__"
        model = Retailer
