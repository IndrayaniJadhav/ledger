import json
import os
from datetime import datetime

from django.utils import six
from django import forms
from django.contrib.postgres.forms import JSONField
from django.forms.widgets import SelectMultiple

from dateutil.relativedelta import relativedelta

from wildlifelicensing.apps.main.models import WildlifeLicence, CommunicationsLogEntry

DATE_FORMAT = '%d/%m/%Y'


class BetterJSONField(JSONField):
    """
    A form field for the JSONField.
    It fixes the double 'stringification', avoid the null text and indents the json (see prepare_value).
    """

    def __init__(self, **kwargs):
        kwargs.setdefault('widget', forms.Textarea(attrs={'cols': 80, 'rows': 20}))
        super(JSONField, self).__init__(**kwargs)

    def prepare_value(self, value):
        if value is None:
            return ""
        if isinstance(value, six.string_types):
            # already a string
            return value
        else:
            return json.dumps(value, indent=4)


class IdentificationForm(forms.Form):
    VALID_FILE_TYPES = ['png', 'jpg', 'jpeg', 'gif', 'pdf', 'PNG', 'JPG', 'JPEG', 'GIF', 'PDF']

    identification_file = forms.FileField(label='Image containing Identification',
                                          help_text='E.g. drivers licence, passport, proof-of-age')

    def clean_identification_file(self):
        id_file = self.cleaned_data.get('identification_file')

        ext = os.path.splitext(str(id_file))[1][1:]

        if ext not in self.VALID_FILE_TYPES:
            raise forms.ValidationError('Uploaded image must be of file type: %s' % ', '.join(self.VALID_FILE_TYPES))

        return id_file


class SeniorCardForm(forms.Form):
    VALID_FILE_TYPES = IdentificationForm.VALID_FILE_TYPES

    senior_card = forms.FileField(label='Senior Card',
                                  help_text='A scan or a photo or your Senior Card')

    def clean_identification_file(self):
        id_file = self.cleaned_data.get('senior_card')

        ext = os.path.splitext(str(id_file))[1][1:]

        if ext not in self.VALID_FILE_TYPES:
            raise forms.ValidationError('Uploaded image must be of file type: %s' % ', '.join(self.VALID_FILE_TYPES))

        return id_file


class IssueLicenceForm(forms.ModelForm):
    ccs = forms.CharField(required=False, label='CCs',
                          help_text="A comma separated list of email addresses you want the licence email to be CC'ed")

    class Meta:
        model = WildlifeLicence
        fields = ['issue_date', 'start_date', 'end_date', 'is_renewable', 'return_frequency', 'regions', 'purpose',
                  'locations',
                  'additional_information', 'cover_letter_message']
        widgets = {
            'regions': SelectMultiple(
                attrs={"class": "hidden"}
            ),
            'purpose': forms.Textarea(attrs={'cols': '40', 'rows': '8'}),
            'locations': forms.Textarea(attrs={'cols': '40', 'rows': '5'}),
            'additional_information': forms.Textarea(attrs={'cols': '40', 'rows': '5'}),
            'cover_letter_message': forms.Textarea(attrs={'cols': '40', 'rows': '5'}),
        }

    def __init__(self, *args, **kwargs):
        purpose = kwargs.pop('purpose', None)

        is_renewable = kwargs.pop('is_renewable', False)

        return_frequency = kwargs.pop('return_frequency', WildlifeLicence.DEFAULT_FREQUENCY)

        skip_required = kwargs.pop('skip_required', False)

        super(IssueLicenceForm, self).__init__(*args, **kwargs)

        if skip_required:
            for field in self.fields.values():
                field.required = False

        if purpose is not None:
            self.fields['purpose'].initial = purpose

        self.fields['is_renewable'].widget = forms.CheckboxInput()

        # if a licence instance has not been passed in nor any POST data (i.e. this is creating the 'get' version of the form)
        if 'instance' not in kwargs and len(args) == 0:
            today_date = datetime.now()
            self.fields['issue_date'].initial = today_date.strftime(DATE_FORMAT)
            self.fields['start_date'].initial = today_date.strftime(DATE_FORMAT)

            self.fields['issue_date'].localize = False

            one_year_today = today_date + relativedelta(years=1, days=-1)

            self.fields['end_date'].initial = one_year_today.strftime(DATE_FORMAT)

            self.fields['is_renewable'].initial = is_renewable

            self.fields['return_frequency'].initial = return_frequency

    def clean(self):
        cleaned_data = super(IssueLicenceForm, self).clean()

        if cleaned_data.get('end_date') < cleaned_data.get('start_date'):
            raise forms.ValidationError('End date must be greater than start date')


class CommunicationsLogEntryForm(forms.ModelForm):
    attachment = forms.FileField(required=False)

    class Meta:
        model = CommunicationsLogEntry
        fields = ['reference', 'to', 'fromm', 'type', 'subject', 'text', 'attachment']

    def __init__(self, *args, **kwargs):
        to = kwargs.pop('to', None)
        fromm = kwargs.pop('fromm', None)
        reference = kwargs.pop('reference', None)

        super(CommunicationsLogEntryForm, self).__init__(*args, **kwargs)

        if to is not None:
            self.fields['to'].initial = to

        if fromm is not None:
            self.fields['fromm'].initial = fromm

        if reference is not None:
            self.fields['reference'].initial = reference
