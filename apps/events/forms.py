# -*- coding: utf-8 -*-
from django import forms
from events.models import Event, AnswerList
from django.utils.translation import ugettext_lazy as _

from django.utils import simplejson
from django.forms.widgets import Textarea
from django.utils.safestring import mark_safe
from django.forms.util import flatatt
from django.utils.html import conditional_escape
from django.utils.encoding import force_unicode

class EventAddressWidget(Textarea):
    def render(self, name, value, attrs=None):
        result = super(EventAddressWidget, self).render(name, value, attrs=attrs)
        result += mark_safe(u'<input style ="float: right; margin-right: 33px; margin-top: 5px;"  type="button" value="Знайти на мапі" onclick="codeAddress()">')
        return result


class EventForm(forms.ModelForm):
    questions = forms.CharField(widget=forms.HiddenInput, required = False)
    location = forms.CharField(initial="(48.464954, 35.044956)", #dnipropetrovsk
                               widget=forms.HiddenInput)
    address = forms.CharField(label = _(u'Адреса проведення'),widget=EventAddressWidget())

    class Meta:
        model = Event
        exclude = ('members', 'creator', 'approved', 'gallery')
        
        
    def __init__(self, user=None, *args, **kwargs):
        self.user = user        
        super(EventForm, self).__init__(*args, **kwargs)
        
class QuestionsForm(forms.Form):
    """
    Dynamic form that allows the user to change
    and then verify the data that was parsed
    """
    def __init__(self, event, user, *args, **kwargs):
        self.event = event
        self.user = user
        super(QuestionsForm, self).__init__(*args, **kwargs)
        
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
        Set the questions in the form
        """
        fields = {}
            
        questions = simplejson.loads(jquestions)
        
        for i, question in enumerate(questions):
            if question['type'] == 'free':
                fields['q'+str(i+1)] = forms.CharField(label=question['title'],
                                                       widget=forms.Textarea)
            else :
                choices_list = []
                for j, option in enumerate(question['options']):
                     choices_list.append((j+1, option))
                if question['type'] == 'one':
                    fields['q'+str(i+1)] = forms.ChoiceField(label=question['title'],
                                                           help_text=_(u"Оберіть одну відповідь"),
                                                           widget=forms.RadioSelect,
                                                           choices=choices_list,
                                                           )
                elif question['type'] == 'multi':
                    fields['q'+str(i+1)] = forms.MultipleChoiceField(label=question['title'],
                                                         help_text = _(u"Оберіть кілька відповідей"),
                                                         widget=forms.CheckboxSelectMultiple,
                                                         choices=choices_list,
                                                         )
            
        self.setFields(fields)
            
    def setData(self, kwds):
        """
        Set the data to include in the form
        """
        for name,field in self.fields.items():
            self.data[name] = field.widget.value_from_datadict(kwds,
                                                               self.files,
                                                               self.add_prefix(name))
        self.is_bound = True
            
    def validate(self, post):
        """
        Validate the contents of the form
        """
        self.cleaned_data = {}
        for name,field in self.fields.items():
            value = field.widget.value_from_datadict(post,
                                                     self.files,
                                                     self.add_prefix(name))
            try:
                self.cleaned_data[name] = field.clean(value)
            except forms.ValidationError, e:
                self.errors[name] = e.messages
                
    def save(self):
        data = [self.cleaned_data[key] for key in sorted(self.cleaned_data.iterkeys())]
        answer_list = AnswerList(event=self.event, user=self.user)
        answer_list.value = simplejson.dumps(data, ensure_ascii = False)
        answer_list.save()
