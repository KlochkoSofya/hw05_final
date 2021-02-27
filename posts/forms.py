from django import forms
from .models import Post, Comment
from django.forms import Textarea


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['group', 'text', 'image']


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
