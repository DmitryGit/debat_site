# -*- coding: utf-8 -*-
from django import forms
from datetime import datetime
from django.utils.translation import ugettext_lazy as _

from photos.models import Image, PhotoSet

class PhotoSetForm(forms.ModelForm):

    class Meta:
        model = PhotoSet
        exclude = ('content_type', 'content_object', 'user', 'publish_type')
    def __init__(self, user = None, *args, **kwargs):
        self.user = user
        super(PhotoSetForm, self).__init__(*args, **kwargs)

class PhotoUploadForm(forms.ModelForm):

    class Meta:
        model = Image
        exclude = ('member', 'title_slug', 'effect', 'crop_from', 'safetylevel',
                   'caption', 'is_public', 'tags', 'photoset')

    def clean_image(self):
        if '#' in self.cleaned_data['image'].name:
            raise forms.ValidationError(
                _("Image filename contains an invalid character: '#'. Please remove the character and try again."))
        return self.cleaned_data['image']

    def __init__(self, user = None, *args, **kwargs):
        self.user = user
        super(PhotoUploadForm, self).__init__(*args, **kwargs)

class PhotoEditForm(forms.ModelForm):

    class Meta:
        model = Image
        exclude = ('member', 'photoset', 'title_slug', 'effect', 'crop_from', 'image')

    def __init__(self, user = None, *args, **kwargs):
        self.user = user
        super(PhotoEditForm, self).__init__(*args, **kwargs)
