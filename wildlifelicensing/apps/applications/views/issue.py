import re
from django.conf import settings
from django.contrib import messages
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, TemplateView

from preserialize.serialize import serialize

from ledger.accounts.models import Document
from wildlifelicensing.apps.main.models import WildlifeLicence,\
    WildlifeLicenceVariantLink
from wildlifelicensing.apps.main.mixins import OfficerRequiredMixin
from wildlifelicensing.apps.main.forms import IssueLicenceForm
from wildlifelicensing.apps.main.pdf import create_licence_pdf_document, create_licence_pdf_bytes,\
    create_cover_letter_pdf_document
from wildlifelicensing.apps.main.signals import licence_issued
from wildlifelicensing.apps.applications.models import Application, Assessment, ApplicationUserAction
from wildlifelicensing.apps.applications.utils import get_log_entry_to, format_application, \
    extract_licence_fields, update_licence_fields
from wildlifelicensing.apps.applications.emails import send_licence_issued_email
from wildlifelicensing.apps.applications.forms import ApplicationLogEntryForm
from wildlifelicensing.apps.payments import utils as payment_utils
from wildlifelicensing.apps.payments.exceptions import PaymentException


LICENCE_TYPE_NUM_CHARS = 2
LICENCE_NUMBER_NUM_CHARS = 6


class IssueLicenceView(OfficerRequiredMixin, TemplateView):
    template_name = 'wl/issue/issue_licence.html'

    def _issue_licence(self, request, application, issue_licence_form):
        # do credit card payment if required
        payment_status = payment_utils.PAYMENT_STATUSES.get(payment_utils.get_application_payment_status(application))

        if payment_status == payment_utils.PAYMENT_STATUS_AWAITING:
            raise PaymentException('Payment is required before licence can be issued')
        elif payment_status == payment_utils.PAYMENT_STATUSES.get(payment_utils.PAYMENT_STATUS_CC_READY):
            payment_utils.invoke_credit_card_payment(application)

        licence = application.licence

        licence.issuer = request.user

        previous_licence = None
        if application.previous_application is not None:
            previous_licence = application.previous_application.licence
            licence.licence_number = previous_licence.licence_number

            # if licence is renewal, start with previous licence's sequence number
            if licence.licence_sequence == 0:
                licence.licence_sequence = previous_licence.licence_sequence

        if not licence.licence_number:
            licence.save(no_revision=True)
            licence.licence_number = '%s-%s' % (str(licence.licence_type.pk).zfill(LICENCE_TYPE_NUM_CHARS),
                                                str(licence.id).zfill(LICENCE_NUMBER_NUM_CHARS))

        # for re-issuing
        original_issue_date = application.licence.issue_date if application.licence.is_issued else None

        licence.licence_sequence += 1

        # reset renewal_sent flag in case of reissue
        licence.renewal_sent = False

        licence_filename = 'licence-%s-%d.pdf' % (licence.licence_number, licence.licence_sequence)

        licence.licence_document = create_licence_pdf_document(licence_filename, licence, application,
                                                               settings.WL_PDF_URL,
                                                               original_issue_date)

        cover_letter_filename = 'cover-letter-%s-%d.pdf' % (licence.licence_number, licence.licence_sequence)

        licence.cover_letter_document = create_cover_letter_pdf_document(cover_letter_filename, licence,
                                                                         request.build_absolute_uri(reverse('home')))

        licence.save()

        if previous_licence is not None:
            previous_licence.replaced_by = licence
            previous_licence.save()

        licence_issued.send(sender=self.__class__, wildlife_licence=licence)

        # update statuses
        application.customer_status = 'approved'
        application.processing_status = 'issued'
        Assessment.objects.filter(application=application, status='awaiting_assessment').\
            update(status='assessment_expired')

        application.save()

        # The licence should be emailed to the customer if they applied for it online. If an officer entered
        # the application on their behalf, the licence needs to be posted to the user.

        # CC's and attachments
        # Rules for emails:
        #  If application lodged by proxy officer and there's a CC list: send email to CCs (to recipients = CCs)
        #  else send the email to customer and if there are CCs put them into the bccs of the email
        ccs = None
        if 'ccs' in issue_licence_form.cleaned_data and issue_licence_form.cleaned_data['ccs']:
            ccs = re.split('[,;]', issue_licence_form.cleaned_data['ccs'])
        attachments = []
        if request.FILES and 'attachments' in request.FILES:
            for _file in request.FILES.getlist('attachments'):
                doc = Document.objects.create(file=_file, name=_file.name)
                attachments.append(doc)

        # check we have an email address to send to
        if licence.profile.email and not licence.profile.user.is_dummy_user:
            to = [licence.profile.email]
            messages.success(request, 'The licence has now been issued and sent as an email attachment to the '
                             'licencee: {}.'.format(licence.profile.email))
            send_licence_issued_email(licence, application, request,
                                      to=to,
                                      bcc=ccs, additional_attachments=attachments)
        else:
            # no email
            messages.success(request, 'The licence has now been issued and must be posted to the licencee. Click '
                             'this link to show the licence <a href="{0}" target="_blank">Licence PDF'
                             '</a><img height="20px" src="{1}"></img> and this link to show the cover letter '
                             '<a href="{2}" target="_blank">Cover Letter PDF</a><img height="20px" src="{3}">'
                             '</img>'.format(licence.licence_document.file.url, static('wl/img/pdf.png'),
                                             licence.cover_letter_document.file.url, static('wl/img/pdf.png')))
            if ccs:
                send_licence_issued_email(licence, application, request, to=ccs, additional_attachments=attachments)

        application.log_user_action(
            ApplicationUserAction.ACTION_ISSUE_LICENCE_.format(licence),
            request
        )

    def get_context_data(self, **kwargs):
        application = get_object_or_404(Application, pk=self.args[0])

        kwargs['application'] = serialize(application, posthook=format_application)

        if application.licence:
            kwargs['issue_licence_form'] = IssueLicenceForm(instance=application.licence)

            kwargs['extracted_fields'] = application.licence.extracted_fields
        else:
            purposes = '\n\n'.join(Assessment.objects.filter(application=application).values_list('purpose', flat=True))

            if hasattr(application.licence_type, 'returntype'):
                return_frequency = application.licence_type.returntype.month_frequency
            else:
                return_frequency = -1

            kwargs['issue_licence_form'] = IssueLicenceForm(purpose=purposes,
                                                            is_renewable=application.licence_type.is_renewable,
                                                            return_frequency=return_frequency)

            kwargs['extracted_fields'] = extract_licence_fields(application.licence_type.application_schema,
                                                                application.data)

        if application.proxy_applicant is None:
            to = application.applicant
        else:
            to = application.proxy_applicant

        kwargs['log_entry_form'] = ApplicationLogEntryForm(to=to.get_full_name(), fromm=self.request.user.get_full_name())

        kwargs['payment_status'] = payment_utils.PAYMENT_STATUSES.get(payment_utils.
                                                                      get_application_payment_status(application))

        return super(IssueLicenceView, self).get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        application = get_object_or_404(Application, pk=self.args[0])

        # get extract fields from licence if it exists, else extract from application data
        if application.licence is not None:
            issue_licence_form = IssueLicenceForm(request.POST, instance=application.licence, files=request.FILES)
            extracted_fields = application.licence.extracted_fields
        else:
            issue_licence_form = IssueLicenceForm(request.POST, files=request.FILES)
            extracted_fields = extract_licence_fields(application.licence_type.application_schema, application.data)

        # update contents of extracted field based on posted data
        extracted_fields = update_licence_fields(extracted_fields, request.POST)

        payment_status = payment_utils.get_application_payment_status(application)
        payment_status_verbose = payment_utils.PAYMENT_STATUSES.get(payment_status)

        log_entry_form = ApplicationLogEntryForm(to=get_log_entry_to(application), fromm=self.request.user.get_full_name())

        if issue_licence_form.is_valid():
            licence = issue_licence_form.save(commit=False)

            # save required fields that aren't contained in the form
            licence.licence_type = application.licence_type
            licence.profile = application.applicant_profile
            licence.holder = application.applicant
            licence.extracted_fields = extracted_fields
            licence.save()

            # clear re-form variants from application
            licence.variants.clear()
            for index, avl in enumerate(application.variants.through.objects.filter(application=application).
                                        order_by('order')):
                WildlifeLicenceVariantLink.objects.create(licence=licence, variant=avl.variant, order=index)

            # save m2m fields of licence (must be done after licence saved)
            issue_licence_form.save_m2m()

            application.licence = licence
            application.save()

            if request.POST.get('submissionType') == 'save':
                messages.success(request, 'Licence saved but not yet issued.')

                return render(request, self.template_name, {
                    'application': serialize(application, posthook=format_application),
                    'issue_licence_form': issue_licence_form,
                    'extracted_fields': extracted_fields,
                    'payment_status': payment_status_verbose,
                    'log_entry_form': log_entry_form
                })
            else:
                try:
                    self._issue_licence(request, application, issue_licence_form)
                except PaymentException as pe:
                    messages.error(request, pe.message)
                    return redirect(request.get_full_path())

                return redirect('wl_dashboard:home')
        else:
            messages.error(request, 'Please fix the errors below before saving / issuing the licence.')

            return render(request, self.template_name, {
                'application': serialize(application, posthook=format_application),
                'issue_licence_form': issue_licence_form,
                'extracted_fields': extracted_fields,
                'payment_status': payment_status_verbose,
                'log_entry_form': log_entry_form
            })


class ReissueLicenceView(OfficerRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        licence = get_object_or_404(WildlifeLicence, pk=self.args[0])

        application = get_object_or_404(Application, licence=licence)

        return redirect('wl_applications:issue_licence', application.pk)


class PreviewLicenceView(OfficerRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        application = get_object_or_404(Application, pk=self.args[0])

        original_issue_date = None
        if application.licence is not None:
            issue_licence_form = IssueLicenceForm(request.GET, instance=application.licence, skip_required=True)
            original_issue_date = application.licence.issue_date
            extracted_fields = application.licence.extracted_fields
        else:
            issue_licence_form = IssueLicenceForm(request.GET, skip_required=True)
            extracted_fields = extract_licence_fields(application.licence_type.application_schema, application.data)

        if issue_licence_form.is_valid():
            licence = issue_licence_form.save(commit=False)
            licence.licence_type = application.licence_type
            licence.profile = application.applicant_profile
            licence.holder = application.applicant
            licence.extracted_fields = update_licence_fields(extracted_fields, request.GET)

            filename = '%s.pdf' % application.lodgement_number

            application.customer_status = 'approved'
            application.processing_status = 'issued'
            application.licence = licence

            response = HttpResponse(content_type='application/pdf')

            response.write(create_licence_pdf_bytes(filename, licence, application,
                                                    settings.WL_PDF_URL,
                                                    original_issue_date))

            return response
        else:
            return HttpResponse('<script type="text/javascript">window.close()</script>')

