# -*- coding: utf-8 -*-
from datetime import datetime
from django import forms
from django.utils.translation import ugettext_lazy as _
from photologue.models import Photo 

from blog.models import Post

import json

class BlogForm(forms.ModelForm):
    
    class Meta:
        model = Post
        exclude = ('author', 'creator_ip', 'created_at', 'updated_at', 'publish', 'status2', 'allow_comments', 'gallery', 'slug')
    
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(BlogForm, self).__init__(*args, **kwargs)            
    
    def clean_slug(self):
        if not self.instance.pk:
            if Post.objects.filter(author=self.user, created_at__month=datetime.now().month, created_at__year=datetime.now().year, slug=self.cleaned_data['slug']).count():
                raise forms.ValidationError(u'This field must be unique for username, year, and month')
            return self.cleaned_data['slug']
        try:
            post = Post.objects.get(author=self.user, created_at__month=self.instance.created_at.month, created_at__year=self.instance.created_at.year, slug=self.cleaned_data['slug'])
            if post != self.instance:
                raise forms.ValidationError(u'This field must be unique for username, year, and month')
        except Post.DoesNotExist:
            pass
        return self.cleaned_data['slug']

class PhotoForm(forms.ModelForm):
    
    class Meta:
        model = Photo
        exclude = ('title', 'title_slug', 'caption', 'crop_from', 'effect', 'tags', 'is_public')
        
