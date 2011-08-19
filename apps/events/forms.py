# -*- coding: utf-8 -*-
from django import forms
from events.models import Event, Member
from django.utils.translation import ugettext_lazy as _

from django.utils import simplejson


class EventForm(forms.ModelForm):
    questions = forms.CharField(widget=forms.widgets.HiddenInput())
    location = forms.CharField(initial="(48.464954, 35.044956)", #dnipropetrovsk
                               widget=forms.widgets.HiddenInput())
    
    class Meta:
        model = Event
        exclude = ('members', 'creator')
        
    def __init__(self, user=None, *args, **kwargs):
        self.user = user        
        super(EventForm, self).__init__(*args, **kwargs)
        
class QuestionsForm(forms.Form):
    """
    Dynamic form that allows the user to change and then verify the data that was parsed
    """
    def setFields(self, kwds):
        """
        Set the fields in the form
        """
        keys = kwds.keys()
        keys.sort()
        for k in keys:
            self.fields[k] = kwds[k]
            
    def setQuestions(self, jquestions):
        """
        Set the fields in the form
        """
        fields = {}
            
        questions = simplejson.loads(jquestions)
        
        for i, question in enumerate(questions):
            if question['type'] == '1':
                help_text = None
                widget = forms.Textarea
            else :
                choices_list = []
                for j, option in enumerate(question['options']):
                     choices_list.append((j+1, option['title']))
                if question['type'] == '2':
                    help_text=_(u"Оберіть одну відповідь")
                    widget = forms.RadioSelect(choices=choices_list)
                elif question['type'] == '3':
                    help_text=_(u"Оберіть кілька відповідей")
                    widget = forms.CheckboxSelectMultiple(choices=choices_list)
            fields['q'+str(i)] = forms.DateField(label=question['title'], help_text = help_text, widget=widget)
            
        self.setFields(fields)
            
    def setData(self, kwds):
        """
        Set the data to include in the form
        """
        keys = kwds.keys()
        keys.sort()
        for k in keys:
            self.data[k] = kwds[k]
            
    def validate(self, post):
        """
        Validate the contents of the form
        """
        for name,field in self.fields.items():
            try:
                field.clean(post[name])
            except ValidationError, e:
                self.errors[name] = e.messages
