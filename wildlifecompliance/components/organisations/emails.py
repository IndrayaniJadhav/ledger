import logging

from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.utils.encoding import smart_text
from django.core.urlresolvers import reverse
from django.conf import settings

from wildlifecompliance.components.emails.emails import TemplateEmailBase

logger = logging.getLogger(__name__)

SYSTEM_NAME = 'Wildlife Compliance Automated Message'
class OrganisationRequestAcceptNotificationEmail(TemplateEmailBase):
    subject = 'Your organisation request has been accepted.'
    html_template = 'wildlifecompliance/emails/organisation_request_accept_notification.html'
    txt_template = 'wildlifecompliance/emails/organisation_request_accept_notification.txt'

class OrganisationRequestAmendmentRequestNotificationEmail(TemplateEmailBase):
    subject = 'Your organisation has requested an amendment to your request.'
    html_template = 'wildlifecompliance/emails/organisation_amendment_requested_notification.html'
    txt_template = 'wildlifecompliance/emails/organisation_amendment_requested_notification.txt'

class OrganisationRequestDeclineNotificationEmail(TemplateEmailBase):
    subject = 'Your organisation request has been declined.'
    html_template = 'wildlifecompliance/emails/organisation_request_decline_notification.html'
    txt_template = 'wildlifecompliance/emails/organisation_request_decline_notification.txt'

class OrganisationLinkNotificationEmail(TemplateEmailBase):
    subject = 'You have been linked to an organisation.'
    html_template = 'wildlifecompliance/emails/organisation_link_notification.html'
    txt_template = 'wildlifecompliance/emails/organisation_link_notification.txt'

class OrganisationUnlinkNotificationEmail(TemplateEmailBase):
    subject = 'You have been unlinked from an organisation.'
    html_template = 'wildlifecompliance/emails/organisation_unlink_notification.html'
    txt_template = 'wildlifecompliance/emails/organisation_unlink_notification.txt'

class OrganisationContactAdminUserNotificationEmail(TemplateEmailBase):
    subject = 'You have been linked as Company Admin Role.'
    html_template = 'wildlifecompliance/emails/organisation_contact_admin_notification.html'
    txt_template = 'wildlifecompliance/emails/organisation_contact_admin_notification.txt'

class OrganisationContactUserNotificationEmail(TemplateEmailBase):
    subject = 'You have been linked as Company User Role.'
    html_template = 'wildlifecompliance/emails/organisation_contact_user_notification.html'
    txt_template = 'wildlifecompliance/emails/organisation_contact_user_notification.txt'

class OrganisationContactSuspendNotificationEmail(TemplateEmailBase):
    subject = 'You have been suspended as Company User.'
    html_template = 'wildlifecompliance/emails/organisation_contact_suspend_notification.html'
    txt_template = 'wildlifecompliance/emails/organisation_contact_suspend_notification.txt'

class OrganisationContactReinstateNotificationEmail(TemplateEmailBase):
    subject = 'You have been Reinstated as Company User.'
    html_template = 'wildlifecompliance/emails/organisation_contact_reinstate_notification.html'
    txt_template = 'wildlifecompliance/emails/organisation_contact_reinstate_notification.txt'

class OrganisationContactDeclineNotificationEmail(TemplateEmailBase):
    subject = 'Your organisation link request has been declined.'
    html_template = 'wildlifecompliance/emails/organisation_contact_decline_notification.html'
    txt_template = 'wildlifecompliance/emails/organisation_contact_decline_notification.txt'

class OrganisationAddressUpdatedNotificationEmail(TemplateEmailBase):
    subject = 'An organisation''s address has been updated.'
    html_template = 'wildlifecompliance/emails/organisation_address_updated_notification.html'
    txt_template = 'wildlifecompliance/emails/organisation_address_updated_notification.txt'

    

def send_organisation_reinstate_email_notification(linked_user,linked_by,organisation,request):
    email = OrganisationContactReinstateNotificationEmail()

    context = {
        'user': linked_user,
        'linked_by': linked_by,
        'organisation': organisation
    }

    msg = email.send(linked_user.email, context=context)
    sender = request.user if request else settings.DEFAULT_FROM_EMAIL
    _log_org_email(msg, organisation, linked_user, sender=sender)


def send_organisation_contact_suspend_email_notification(linked_user,linked_by,organisation,request):
    email = OrganisationContactSuspendNotificationEmail()

    context = {
        'user': linked_user,
        'linked_by': linked_by,
        'organisation': organisation
    }

    msg = email.send(linked_user.email, context=context)
    sender = request.user if request else settings.DEFAULT_FROM_EMAIL
    _log_org_email(msg, organisation, linked_user, sender=sender)

def send_organisation_contact_decline_email_notification(user_contact,deleted_by,organisation,request):
    email = OrganisationContactDeclineNotificationEmail()

    context = {
        'user': user_contact,
        'linked_by': deleted_by,
        'organisation': organisation
    }

    msg = email.send(user_contact.email, context=context)
    sender = request.user if request else settings.DEFAULT_FROM_EMAIL
    _log_org_email(msg, organisation, user_contact, sender=sender)



def send_organisation_contact_user_email_notification(linked_user,linked_by,organisation,request):
    email = OrganisationContactUserNotificationEmail()

    context = {
        'user': linked_user,
        'linked_by': linked_by,
        'organisation': organisation
    }

    msg = email.send(linked_user.email, context=context)
    sender = request.user if request else settings.DEFAULT_FROM_EMAIL
    _log_org_email(msg, organisation, linked_user, sender=sender)


def send_organisation_contact_adminuser_email_notification(linked_user,linked_by,organisation,request):
    email = OrganisationContactAdminUserNotificationEmail()

    context = {
        'user': linked_user,
        'linked_by': linked_by,
        'organisation': organisation
    }

    msg = email.send(linked_user.email, context=context)
    sender = request.user if request else settings.DEFAULT_FROM_EMAIL
    _log_org_email(msg, organisation, linked_user, sender=sender)



def send_organisation_link_email_notification(linked_user,linked_by,organisation,request):
    email = OrganisationLinkNotificationEmail()

    context = {
        'user': linked_user,
        'linked_by': linked_by,
        'organisation': organisation
    }

    msg = email.send(linked_user.email, context=context)
    sender = request.user if request else settings.DEFAULT_FROM_EMAIL
    _log_org_email(msg, organisation, linked_user, sender=sender)

def send_organisation_unlink_email_notification(unlinked_user,unlinked_by,organisation,request):
    email = OrganisationUnlinkNotificationEmail()

    context = {
        'user': unlinked_user,
        'unlinked_by': unlinked_by,
        'organisation': organisation
    }

    msg = email.send(unlinked_user.email, context=context)
    sender = request.user if request else settings.DEFAULT_FROM_EMAIL
    _log_org_email(msg, organisation, unlinked_user, sender=sender)

def send_organisation_request_accept_email_notification(org_request,organisation,request):
    email = OrganisationRequestAcceptNotificationEmail()
    context = {
        'request': org_request
    }

    msg = email.send(org_request.requester.email, context=context)
    sender = request.user if request else settings.DEFAULT_FROM_EMAIL
    _log_org_request_email(msg, org_request, sender=sender)
    # _log_org_email(msg, organisation, org_request.requester, sender=sender)

def send_organisation_request_amendment_requested_email_notification(org_request,organisation,request):
    email = OrganisationRequestAmendmentRequestNotificationEmail()
    context = {
        'request': org_request,
        'reason': request.query_params.get('reason').split('.json')[0]
    }

    msg = email.send(org_request.requester.email, context=context)
    sender = request.user if request else settings.DEFAULT_FROM_EMAIL
    _log_org_request_email(msg, org_request, sender=sender)
    # _log_org_email(msg, organisation, org_request.requester, sender=sender)

def send_organisation_request_decline_email_notification(org_request,request):
    email = OrganisationRequestDeclineNotificationEmail()

    context = {
        'request': org_request
    }

    msg = email.send(org_request.requester.email, context=context)
    sender = request.user if request else settings.DEFAULT_FROM_EMAIL
    _log_org_request_email(msg, org_request, sender=sender)
    # _log_org_email(msg, organisation, org_request.requester, sender=sender)

def send_organisation_address_updated_email_notification(address_updated_by,ledger_organisation,wc_organisation,request):
    from wildlifecompliance.components.organisations.models import OrganisationContact

    email = OrganisationAddressUpdatedNotificationEmail()

    context = {
        'address_updated_by': address_updated_by,
        'organisation': ledger_organisation
    }

    for org_contact in OrganisationContact.objects.filter(user_role='organisation_admin',organisation=wc_organisation):
        msg = email.send(org_contact.email, context=context)
        sender = request.user if request else settings.DEFAULT_FROM_EMAIL

        # TODO change this to log an entry for organisation audit records instead of organisation request
        # _log_org_request_email(msg, request, sender=sender)
    # _log_org_email(msg, organisation, org_request.requester, sender=sender)

def _log_org_request_email(email_message, request, sender=None):
    from wildlifecompliance.components.organisations.models import OrganisationRequestLogEntry
    if isinstance(email_message, (EmailMultiAlternatives, EmailMessage,)):
        # TODO this will log the plain text body, should we log the html instead
        text = email_message.body
        subject = email_message.subject
        fromm = smart_text(sender) if sender else smart_text(email_message.from_email)
        # the to email is normally a list
        if isinstance(email_message.to, list):
            to = ','.join(email_message.to)
        else:
            to = smart_text(email_message.to)
        # we log the cc and bcc in the same cc field of the log entry as a ',' comma separated string
        all_ccs = []
        if email_message.cc:
            all_ccs += list(email_message.cc)
        if email_message.bcc:
            all_ccs += list(email_message.bcc)
        all_ccs = ','.join(all_ccs)

    else:
        text = smart_text(email_message)
        subject = ''
        to = request.requester.email
        fromm = smart_text(sender) if sender else SYSTEM_NAME
        all_ccs = ''

    customer = request.requester

    staff = sender

    kwargs = {
        'subject': subject,
        'text': text,
        'request': request,
        'customer': customer,
        'staff': staff,
        'to': to,
        'fromm': fromm,
        'cc': all_ccs
    }

    email_entry = OrganisationRequestLogEntry.objects.create(**kwargs)

    return email_entry

def _log_org_email(email_message, organisation, customer ,sender=None):
    from wildlifecompliance.components.organisations.models import OrganisationLogEntry
    if isinstance(email_message, (EmailMultiAlternatives, EmailMessage,)):
        # TODO this will log the plain text body, should we log the html instead
        text = email_message.body
        subject = email_message.subject
        fromm = smart_text(sender) if sender else smart_text(email_message.from_email)
        # the to email is normally a list
        if isinstance(email_message.to, list):
            to = ','.join(email_message.to)
        else:
            to = smart_text(email_message.to)
        # we log the cc and bcc in the same cc field of the log entry as a ',' comma separated string
        all_ccs = []
        if email_message.cc:
            all_ccs += list(email_message.cc)
        if email_message.bcc:
            all_ccs += list(email_message.bcc)
        all_ccs = ','.join(all_ccs)

    else:
        text = smart_text(email_message)
        subject = ''
        to = request.requester.email
        fromm = smart_text(sender) if sender else SYSTEM_NAME
        all_ccs = ''

    customer = customer

    staff = sender

    kwargs = {
        'subject': subject,
        'text': text,
        'organisation': organisation,
        'customer': customer,
        'staff': staff,
        'to': to,
        'fromm': fromm,
        'cc': all_ccs
    }

    email_entry = OrganisationLogEntry.objects.create(**kwargs)

    return email_entry
