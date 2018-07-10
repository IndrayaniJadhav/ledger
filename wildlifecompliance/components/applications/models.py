from __future__ import unicode_literals

import json
import datetime
from django.db import models,transaction
from django.dispatch import receiver
from django.db.models.signals import pre_delete
from django.utils.encoding import python_2_unicode_compatible
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields.jsonb import JSONField
from django.utils import timezone
from django.contrib.sites.models import Site
from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase
from ledger.accounts.models import Organisation as ledger_organisation
from ledger.accounts.models import EmailUser, RevisionedMixin
from ledger.licence.models import Licence
from wildlifecompliance import exceptions

from wildlifecompliance.components.organisations.models import Organisation
from wildlifecompliance.components.main.models import CommunicationsLogEntry, Region, UserAction, Document
from wildlifecompliance.components.main.utils import get_department_user
from wildlifecompliance.components.applications.email import send_referral_email_notification
from wildlifecompliance.ordered_model import OrderedModel




def update_application_doc_filename(instance, filename):
    return 'applications/{}/documents/{}'.format(instance.application.id,filename)

def update_application_comms_log_filename(instance, filename):
    return 'applications/{}/communications/{}/{}'.format(instance.log_entry.application.id,instance.id,filename)

class ApplicationType(models.Model):
    schema = JSONField()
    activities = TaggableManager(verbose_name="Activities",help_text="A comma-separated list of activities.")
    site = models.OneToOneField(Site, default='1')

    class Meta:
        app_label = 'wildlifecompliance'


class TaggedApplicationAssessorGroupRegions(TaggedItemBase):
    content_object = models.ForeignKey("ApplicationAssessorGroup")

    class Meta:
        app_label = 'wildlifecompliance'

class TaggedApplicationAssessorGroupActivities(TaggedItemBase):
    content_object = models.ForeignKey("ApplicationAssessorGroup")

    class Meta:
        app_label = 'wildlifecompliance'

class ApplicationAssessorGroup(models.Model):
    name = models.CharField(max_length=255)
    members = models.ManyToManyField(EmailUser,blank=True)
    regions = TaggableManager(verbose_name="Regions",help_text="A comma-separated list of regions.",through=TaggedApplicationAssessorGroupRegions,related_name = "+",blank=True)
    activities = TaggableManager(verbose_name="Activities",help_text="A comma-separated list of activities.",through=TaggedApplicationAssessorGroupActivities,related_name = "+",blank=True)
    default = models.BooleanField(default=False)

    class Meta:
        app_label = 'wildlifecompliance'

    def __str__(self):
        return self.name

    def clean(self):
        try:
            default = ApplicationAssessorGroup.objects.get(default=True)
        except ApplicationAssessorGroup.DoesNotExist:
            default = None

        if default and self.pk:
            if int(self.pk) != int(default.id):
                if default and self.default:
                    raise ValidationError('There can only be one default application assessor group')
        else:
            if default and self.default:
                raise ValidationError('There can only be one default application assessor group')

    def member_is_assigned(self,member):
        for p in self.current_applications:
            if p.assigned_officer == member:
                return True
        return False

    @property
    def current_applications(self):
        assessable_states = ['with_assessor','with_referral','with_assessor_conditions'] 
        return Application.objects.filter(processing_status__in=assessable_states)
        
class TaggedApplicationApproverGroupRegions(TaggedItemBase):
    content_object = models.ForeignKey("ApplicationApproverGroup")

    class Meta:
        app_label = 'wildlifecompliance'

class TaggedApplicationApproverGroupActivities(TaggedItemBase):
    content_object = models.ForeignKey("ApplicationApproverGroup")

    class Meta:
        app_label = 'wildlifecompliance'

class ApplicationApproverGroup(models.Model):
    name = models.CharField(max_length=255)
    members = models.ManyToManyField(EmailUser,blank=True)
    regions = TaggableManager(verbose_name="Regions",help_text="A comma-separated list of regions.",through=TaggedApplicationApproverGroupRegions,related_name = "+",blank=True)
    activities = TaggableManager(verbose_name="Activities",help_text="A comma-separated list of activities.",through=TaggedApplicationApproverGroupActivities,related_name = "+",blank=True)
    default = models.BooleanField(default=False)

    class Meta:
        app_label = 'wildlifecompliance'

    def __str__(self):
        return self.name

    def clean(self):
        try:
            default = ApplicationApproverGroup.objects.get(default=True)
        except ApplicationApproverGroup.DoesNotExist:
            default = None

        if default and self.pk:
            if int(self.pk) != int(default.id):
                if default and self.default:
                    raise ValidationError('There can only be one default application approver group')
        else:
            if default and self.default:
                raise ValidationError('There can only be one default application approver group')

    def member_is_assigned(self,member):
        for p in self.current_applications:
            if p.assigned_approver == member:
                return True
        return False

    @property
    def current_applications(self):
        assessable_states = ['with_approver'] 
        return Application.objects.filter(processing_status__in=assessable_states)
        
class ApplicationDocument(Document):
    application = models.ForeignKey('Application',related_name='documents')
    _file = models.FileField(upload_to=update_application_doc_filename)
    input_name = models.CharField(max_length=255,null=True,blank=True)

    class Meta:
        app_label = 'wildlifecompliance'

class Application(RevisionedMixin):

    CUSTOMER_STATUS_CHOICES = (('draft', 'Draft'),
                               ('under_review', 'Under Review'),
                               ('amendment_required', 'Amendment Required'),
                               ('accepted', 'Accepted'),
                               ('partially_accepted', 'Partially Accepted'),
                               ('declined', 'Declined'),
                               )

    # List of statuses from above that allow a customer to edit an application.
    CUSTOMER_EDITABLE_STATE = ['temp',
                                'draft',
                                'amendment_required',
                            ]

    # List of statuses from above that allow a customer to view an application (read-only)
    CUSTOMER_VIEWABLE_STATE = ['with_assessor', 'under_review', 'id_required', 'returns_required', 'approved', 'declined']

    PROCESSING_STATUS_CHOICES = (('draft', 'Draft'), 
                                 ('with_officer', 'With Officer'), 
                                 ('with_assessor', 'With Assessor'),
                                 ('with_referral', 'With Referral'),
                                 ('with_assessor_conditions', 'With Assessor (Conditions)'),
                                 ('with_approver', 'With Approver'),
                                 ('renewal', 'Renewal'),
                                 ('licence_amendment', 'Licence Amendment'), 
                                 ('awaiting_applicant_response', 'Awaiting Applicant Response'),
                                 ('awaiting_assessor_response', 'Awaiting Assessor Response'),
                                 ('awaiting_responses', 'Awaiting Responses'),
                                 ('ready_for_conditions', 'Ready for Conditions'),
                                 ('ready_to_issue', 'Ready to Issue'),
                                 ('approved', 'Approved'),
                                 ('declined', 'Declined'),
                                 ('discarded', 'Discarded'),
                                 )

    ID_CHECK_STATUS_CHOICES = (('not_checked', 'Not Checked'), ('awaiting_update', 'Awaiting Update'),
                               ('updated', 'Updated'), ('accepted', 'Accepted'))

    RETURN_CHECK_STATUS_CHOICES = (
        ('not_checked', 'Not Checked'), ('awaiting_returns', 'Awaiting Returns'), ('completed', 'Completed'),
        ('accepted', 'Accepted'))

    CHARACTER_CHECK_STATUS_CHOICES = (
        ('not_checked', 'Not Checked'), ('accepted', 'Accepted'))

    REVIEW_STATUS_CHOICES = (
        ('not_reviewed', 'Not Reviewed'), ('awaiting_amendments', 'Awaiting Amendments'), ('amended', 'Amended'),
        ('accepted', 'Accepted'))

    APPLICATION_TYPE_CHOICES = (
        ('new_licence', 'New Licence'),
        ('amendment', 'Amendment'),
        ('renewal', 'Renewal'),
    )

    application_type = models.CharField('Application Type', max_length=40, choices=APPLICATION_TYPE_CHOICES,
                                        default=APPLICATION_TYPE_CHOICES[0][0])
    data = JSONField(blank=True, null=True)
    assessor_data = JSONField(blank=True, null=True)
    comment_data = JSONField(blank=True, null=True)
    licence_type_data = JSONField(blank=True, null=True)
    schema = JSONField(blank=False, null=False)
    proposed_issuance_licence = JSONField(blank=True, null=True)
    #hard_copy = models.ForeignKey(Document, blank=True, null=True, related_name='hard_copy')

    customer_status = models.CharField('Customer Status', max_length=40, choices=CUSTOMER_STATUS_CHOICES,
                                       default=CUSTOMER_STATUS_CHOICES[0][0])
    applicant = models.ForeignKey(Organisation, blank=True, null=True, related_name='applications')

    lodgement_number = models.CharField(max_length=9, blank=True, default='')
    lodgement_sequence = models.IntegerField(blank=True, default=0)
    lodgement_date = models.DateField(blank=True, null=True)

    proxy_applicant = models.ForeignKey(EmailUser, blank=True, null=True, related_name='wildlifecompliance_proxy')
    submitter = models.ForeignKey(EmailUser, blank=True, null=True, related_name='wildlifecompliance_applications')

    assigned_officer = models.ForeignKey(EmailUser, blank=True, null=True, related_name='wildlifecompliance_applications_assigned')
    assigned_approver = models.ForeignKey(EmailUser, blank=True, null=True, related_name='wildlifecompliance_applications_licences')
    processing_status = models.CharField('Processing Status', max_length=30, choices=PROCESSING_STATUS_CHOICES,
                                         default=PROCESSING_STATUS_CHOICES[0][0])
    id_check_status = models.CharField('Identification Check Status', max_length=30, choices=ID_CHECK_STATUS_CHOICES,
                                       default=ID_CHECK_STATUS_CHOICES[0][0])
    return_check_status = models.CharField('Return Check Status', max_length=30, choices=RETURN_CHECK_STATUS_CHOICES,
                                            default=RETURN_CHECK_STATUS_CHOICES[0][0])
    character_check_status = models.CharField('Character Check Status', max_length=30,
                                              choices=CHARACTER_CHECK_STATUS_CHOICES,
                                              default=CHARACTER_CHECK_STATUS_CHOICES[0][0])
    review_status = models.CharField('Review Status', max_length=30, choices=REVIEW_STATUS_CHOICES,
                                     default=REVIEW_STATUS_CHOICES[0][0])

    licence = models.ForeignKey('wildlifecompliance.WildlifeLicence',null=True,blank=True)

    previous_application = models.ForeignKey('self', on_delete=models.PROTECT, blank=True, null=True)
    proposed_decline_status = models.BooleanField(default=False)
    # Special Fields
    activity = models.CharField(max_length=255,null=True,blank=True)
    region = models.CharField(max_length=255,null=True,blank=True)
    title = models.CharField(max_length=255,null=True,blank=True)
    tenure = models.CharField(max_length=255,null=True,blank=True)

    # licence_class = models.ForeignKey('wildlifecompliance.WildlifeLicenceClass',blank=True,null=True)
    # licence_activity_type= models.ForeignKey('wildlifecompliance.WildlifeLicenceActivityType',blank=True,null=True)
    # licence_activity= models.ForeignKey('wildlifecompliance.WildlifeLicenceActivity',blank=True,null=True)

    class Meta:
        app_label = 'wildlifecompliance'

    def __str__(self):
        return str(self.id)

    @property
    def reference(self):
        return '{}-{}'.format(self.lodgement_number, self.lodgement_sequence)

    @property
    def is_assigned(self):
        return self.assigned_officer is not None

    @property
    def is_temporary(self):
        return self.customer_status == 'temp' and self.processing_status == 'temp'

    @property
    def can_user_edit(self):
        """
        :return: True if the application is in one of the editable status.
        """
        return self.customer_status in self.CUSTOMER_EDITABLE_STATE

    @property
    def can_user_view(self):
        """
        :return: True if the application is in one of the approved status.
        """
        return self.customer_status in self.CUSTOMER_VIEWABLE_STATE

    @property
    def is_discardable(self):
        """
        An application can be discarded by a customer if:
        1 - It is a draft
        2- or if the application has been pushed back to the user
        """
        return self.customer_status == 'draft' or self.processing_status == 'awaiting_applicant_response'

    @property
    def is_deletable(self):
        """
        An application can be deleted only if it is a draft and it hasn't been lodged yet
        :return:
        """
        return self.customer_status == 'draft' and not self.lodgement_number

    @property
    def latest_referrals(self):
        return self.referrals.all()[:2]

    @property
    def regions_list(self):
        return self.region.split(',') if self.region else []

    @property
    def permit(self):
        return self.licence.licence_document._file.url if self.licence else None

    @property
    def allowed_assessors(self):
        if self.processing_status == 'with_approver':
            group = self.__approver_group()
        else:
            group = self.__assessor_group()
        return group.members.all() if group else []

    def __assessor_group(self):
        # TODO get list of assessor groups based on region and activity
        if self.region and self.activity:
            try:
                check_group = ApplicationAssessorGroup.objects.filter(
                    activities__name__in=[self.activity],
                    regions__name__in=self.regions_list         
                ).distinct()
                if check_group:
                    return check_group[0]
            except ApplicationAssessorGroup.DoesNotExist:
                pass
        default_group = ApplicationAssessorGroup.objects.get(default=True)
 
        return default_group

    def __approver_group(self):
        # TODO get list of approver groups based on region and activity
        if self.region and self.activity:
            try:
                check_group = ApplicationApproverGroup.objects.filter(
                    activities__name__in=[self.activity],
                    regions__name__in=self.regions_list         
                ).distinct()
                if check_group:
                    return check_group[0]
            except ApplicationApproverGroup.DoesNotExist:
                pass
        default_group = ApplicationApproverGroup.objects.get(default=True)
 
        return default_group

    def __check_application_filled_out(self):
        if not self.data:
            raise exceptions.ApplicationNotComplete()
        missing_fields = []
        required_fields = {
            'region':'Region/District',
            'title': 'Title',
            'activity': 'Activity'
        }
        for k,v in required_fields.items():
            val = getattr(self,k)
            if not val:
                missing_fields.append(v)
        return missing_fields

    def can_assess(self,user):
        if self.processing_status == 'with_assessor' or self.processing_status == 'with_referral' or self.processing_status == 'with_assessor_conditions':
            return self.__assessor_group() in user.applicationassessorgroup_set.all()
        elif self.processing_status == 'with_approver':
            return self.__approver_group() in user.applicationapprovergroup_set.all()
        else:
            return False

    def has_assessor_mode(self,user):
        status_without_assessor = ['with_approver','approved','declined']
        if self.processing_status in status_without_assessor: 
            return False
        else:
            if self.assigned_officer: 
                if self.assigned_officer == user:
                    return self.__assessor_group() in user.applicationassessorgroup_set.all()
                else:
                    return False
            else:
                return self.__assessor_group() in user.applicationassessorgroup_set.all()
        
    def log_user_action(self, action, request):
        return ApplicationUserAction.log_action(self, action, request.user)

    def submit(self,request,viewset):
        from wildlifecompliance.components.applications.utils import save_proponent_data 
        with transaction.atomic():
            if self.can_user_edit:
                # Save the data first
                save_proponent_data(self,request,viewset)
                # Check if the special fields have been completed
                # missing_fields = self.__check_application_filled_out()
                # if missing_fields:
                #     error_text = 'The application has these missing fields, {}'.format(','.join(missing_fields))
                #     raise exceptions.ApplicationMissingFields(detail=error_text)
                self.processing_status = 'under_review'
                self.customer_status = 'under_review'
                self.submitter = request.user
                self.lodgement_date = datetime.datetime.strptime(timezone.now().strftime('%Y-%m-%d'),'%Y-%m-%d').date()
                self.save()
                # Create a log entry for the application
                self.log_user_action(ApplicationUserAction.ACTION_LODGE_APPLICATION.format(self.id),request)
                # Create a log entry for the organisation
                self.applicant.log_user_action(ApplicationUserAction.ACTION_LODGE_APPLICATION.format(self.id),request)
            else:
                raise ValidationError('You can\'t edit this application at this moment')

    def accept_id_check(self,request):
            self.id_check_status = 'accepted'
            self.save()
            # Create a log entry for the application
            self.log_user_action(ApplicationUserAction.ACTION_ACCEPT_ID.format(self.id),request)
            # Create a log entry for the organisation
            self.applicant.log_user_action(ApplicationUserAction.ACTION_ACCEPT_ID.format(self.id),request)
            
    def request_id_check(self,request):
            self.id_check_status = 'awaiting_update'
            self.save()
            # Create a log entry for the application
            self.log_user_action(ApplicationUserAction.ACTION_ID_REQUEST_UPDATE.format(self.id),request)
            # Create a log entry for the organisation
            self.applicant.log_user_action(ApplicationUserAction.ACTION_ID_REQUEST_UPDATE.format(self.id),request)


    def accept_character_check(self,request):
            self.character_check_status = 'accepted'
            self.save()
            # Create a log entry for the application
            self.log_user_action(ApplicationUserAction.ACTION_ACCEPT_CHARACTER.format(self.id),request)
            # Create a log entry for the organisation
            self.applicant.log_user_action(ApplicationUserAction.ACTION_ACCEPT_CHARACTER.format(self.id),request)    

    def send_to_assessor(self,request):
            self.processing_status = 'with_assessor'
            self.save()
            # Create a log entry for the application
            self.log_user_action(ApplicationUserAction.ACTION_ACCEPT_CHARACTER.format(self.id),request)
            # Create a log entry for the organisation
            self.applicant.log_user_action(ApplicationUserAction.ACTION_ACCEPT_CHARACTER.format(self.id),request)        


    def send_referral(self,request,referral_email):
        with transaction.atomic():
            try:
                if self.processing_status == 'with_assessor' or self.processing_status == 'with_referral':
                    self.processing_status = 'with_referral'
                    self.save()
                    referral = None

                    # Check if the user is in ledger
                    try:
                        user = EmailUser.objects.get(email__icontains=referral_email)
                    except EmailUser.DoesNotExist:
                        # Validate if it is a deparment user
                        department_user = get_department_user(referral_email)
                        if not department_user:
                            raise ValidationError('The user you want to send the referral to is not a member of the department')
                        # Check if the user is in ledger or create
                        
                        user,created = EmailUser.objects.get_or_create(email=department_user['email'].lower())
                        if created:
                            user.first_name = department_user['given_name']
                            user.last_name = department_user['surname']
                            user.save()
                    try:
                        Referral.objects.get(referral=user,application=self)
                        raise ValidationError('A referral has already been sent to this user')
                    except Referral.DoesNotExist:
                        # Create Referral
                        referral = Referral.objects.create(
                            application = self,
                            referral=user,
                            sent_by=request.user 
                        )
                    # Create a log entry for the application
                    self.log_user_action(ApplicationUserAction.ACTION_SEND_REFERRAL_TO.format(referral.id,self.id,'{}({})'.format(user.get_full_name(),user.email)),request)
                    # Create a log entry for the organisation
                    self.applicant.log_user_action(ApplicationUserAction.ACTION_SEND_REFERRAL_TO.format(referral.id,self.id,'{}({})'.format(user.get_full_name(),user.email)),request)
                    # send email
                    send_referral_email_notification(referral,request)
                else:
                    raise exceptions.ApplicationReferralCannotBeSent()
            except:
                raise

    def assign_officer(self,request,officer):
        with transaction.atomic():
            try:
                if not self.can_assess(request.user):
                    raise exceptions.ApplicationNotAuthorized() 
                if not self.can_assess(officer):
                    raise ValidationError('The selected person is not authorised to be assigned to this application')
                if self.processing_status == 'with_approver':
                    if officer != self.assigned_approver:
                        self.assigned_approver = officer
                        self.save()
                        # Create a log entry for the application
                        self.log_user_action(ApplicationUserAction.ACTION_ASSIGN_TO_APPROVER.format(self.id,'{}({})'.format(officer.get_full_name(),officer.email)),request)
                        # Create a log entry for the organisation
                        self.applicant.log_user_action(ApplicationUserAction.ACTION_ASSIGN_TO_APPROVER.format(self.id,'{}({})'.format(officer.get_full_name(),officer.email)),request)
                else:
                    if officer != self.assigned_officer:
                        self.assigned_officer = officer
                        self.save()
                        # Create a log entry for the application
                        self.log_user_action(ApplicationUserAction.ACTION_ASSIGN_TO_ASSESSOR.format(self.id,'{}({})'.format(officer.get_full_name(),officer.email)),request)
                        # Create a log entry for the organisation
                        self.applicant.log_user_action(ApplicationUserAction.ACTION_ASSIGN_TO_ASSESSOR.format(self.id,'{}({})'.format(officer.get_full_name(),officer.email)),request)
            except:
                raise

    def unassign(self,request):
        with transaction.atomic():
            try:
                if not self.can_assess(request.user):
                    raise exceptions.ApplicationNotAuthorized() 
                if self.processing_status == 'with_approver':
                    if self.assigned_approver:
                        self.assigned_approver = None 
                        self.save()
                        # Create a log entry for the application
                        self.log_user_action(ApplicationUserAction.ACTION_UNASSIGN_APPROVER.format(self.id),request)
                        # Create a log entry for the organisation
                        self.applicant.log_user_action(ApplicationUserAction.ACTION_UNASSIGN_APPROVER.format(self.id),request)
                else:
                    if self.assigned_officer:
                        self.assigned_officer = None 
                        self.save()
                        # Create a log entry for the application
                        self.log_user_action(ApplicationUserAction.ACTION_UNASSIGN_ASSESSOR.format(self.id),request)
                        # Create a log entry for the organisation
                        self.applicant.log_user_action(ApplicationUserAction.ACTION_UNASSIGN_ASSESSOR.format(self.id),request)
            except:
                raise

    def move_to_status(self,request,status):
        if not self.can_assess(request.user):
            raise exceptions.ApplicationNotAuthorized()
        if status in ['with_assessor','with_assessor_conditions','with_approver']:
            # Code from disturbance
            # if self.processing_status == 'with_referral' or self.can_user_edit:
            #     raise ValidationError('You cannot change the current status at this time')
            if self.processing_status != status:
                self.processing_status = status
                self.save()
        else:
            raise ValidationError('The provided status cannot be found.')

    def proposed_decline(self,request,details):
        with transaction.atomic():
            try:
                if not self.can_assess(request.user):
                    raise exceptions.ApplicationNotAuthorized()
                if self.processing_status != 'with_assessor':
                    raise ValidationError('You cannot propose to decline if it is not with assessor')

                ApplicationDeclinedDetails.objects.update_or_create(
                    application = self,
                    defaults={'officer':request.user,'reason':details.get('reason'),'cc_email':details.get('cc_email',None)}
                )
                self.proposed_decline_status = True
                self.move_to_status(request,'with_approver')
                # Log application action
                self.log_user_action(ApplicationUserAction.ACTION_PROPOSED_DECLINE.format(self.id),request)
                # Log entry for organisation
                self.applicant.log_user_action(ApplicationUserAction.ACTION_PROPOSED_DECLINE.format(self.id),request)
            except:
                raise

    def final_decline(self,request,details):
        with transaction.atomic():
            try:
                if not self.can_assess(request.user):
                    raise exceptions.ApplicationNotAuthorized()
                if self.processing_status != 'with_approver':
                    raise ValidationError('You cannot decline if it is not with approver')

                ApplicationDeclinedDetails.objects.update_or_create(
                    application = self,
                    defaults={'officer':request.user,'reason':details.get('reason'),'cc_email':details.get('cc_email',None)}
                )
                self.proposed_decline_status = True
                self.processing_status = 'declined'
                self.customer_status = 'declined'
                self.save()
                # Log application action
                self.log_user_action(ApplicationUserAction.ACTION_DECLINE.format(self.id),request)
                # Log entry for organisation
                self.applicant.log_user_action(ApplicationUserAction.ACTION_DECLINE.format(self.id),request)
            except:
                raise

    def proposed_licence(self,request,details):
        with transaction.atomic():
            try:
                if not self.can_assess(request.user):
                    raise exceptions.ApplicationNotAuthorized()
                if self.processing_status != 'with_assessor_conditions':
                    raise ValidationError('You cannot propose for licence if it is not with assessor for conditions')
                self.proposed_issuance_licence = {
                    'start_date' : details.get('start_date').strftime('%d/%m/%Y'),
                    'expiry_date' : details.get('expiry_date').strftime('%d/%m/%Y'),
                    'details': details.get('details'),
                    'cc_email':details.get('cc_email')
                }
                self.proposed_decline_status = False
                self.move_to_status(request,'with_approver')
                # Log application action
                self.log_user_action(ApplicationUserAction.ACTION_PROPOSED_LICENCE.format(self.id),request)
                # Log entry for organisation
                self.applicant.log_user_action(ApplicationUserAction.ACTION_PROPOSED_LICENCE.format(self.id),request)
            except:
                raise

    def final_licence(self,request,details):
        from wildlifecompliance.components.licences.models import WildlifeLicence
        with transaction.atomic():
            try:
                if not self.can_assess(request.user):
                    raise exceptions.ApplicationNotAuthorized()
                if self.processing_status != 'with_approver':
                    raise ValidationError('You cannot issue the licence if it is not with an approver')
                if not self.applicant.organisation.postal_address:
                    raise ValidationError('The applicant needs to have set their postal address before approving this application.')

                self.proposed_issuance_licence = {
                    'start_date' : details.get('start_date').strftime('%d/%m/%Y'),
                    'expiry_date' : details.get('expiry_date').strftime('%d/%m/%Y'),
                    'details': details.get('details'),
                    'cc_email':details.get('cc_email')
                }
                self.proposed_decline_status = False
                self.processing_status = 'approved'
                self.customer_status = 'approved'
                # Log application action
                self.log_user_action(ApplicationUserAction.ACTION_ISSUE_LICENCE_.format(self.id),request)
                # Log entry for organisation
                self.applicant.log_user_action(ApplicationUserAction.ACTION_ISSUE_LICENCE_.format(self.id),request)

                if self.processing_status == 'approved':
                    # TODO if it is an ammendment application then check appropriately
                    checking_application = self
                    licence,created = WildlifeLicence.objects.update_or_create(
                        current_application = checking_application,
                        defaults = {
                            'activity' : self.activity,
                            'region' : self.region, 
                            'tenure' : self.tenure, 
                            'title' : self.title,
                            'issue_date' : timezone.now(),
                            'expiry_date' : details.get('expiry_date'),
                            'start_date' : details.get('start_date'),
                            'applicant' : self.applicant 
                            #'extracted_fields' = JSONField(blank=True, null=True)
                        }
                    )
                    # Generate returns 
                    self.generate_returns(licence)
                    if created:
                        # Log creation
                        # Generate the document
                        licence.generate_doc()
                        # send the doc and log in licence and org
                    else:
                        # Log update
                        licence.replaced_by = request.user
                        # Generate the document
                        licence.generate_doc()
                        # send the doc and log in licence and org
                    self.licence = licence
                self.save()
        
            except:
                raise

    def generate_returns(self,licence):
        from wildlifecompliance.components.returns.models import Return
        today = timezone.now().date()
        timedelta = datetime.timedelta
        for req in self.conditions.all():
            if req.recurrence and req.due_date > today:
                current_date = req.due_date
                for x in range(req.recurrence_schedule):
                    #Weekly
                    if req.recurrence_pattern == 1:
                        current_date += timedelta(weeks=1)
                    #Monthly
                    elif req.recurrence_pattern == 2:
                        current_date += timedelta(weeks=4)
                        pass
                    #Yearly
                    elif req.recurrence_pattern == 3:
                        current_date += timedelta(days=365)
                    # Create the return
                    Return.objects.create(
                        application=self,
                        due_date=current_date,
                        processing_status='future',
                        licence=licence
                    )
                    #TODO add logging for return 

class ApplicationLogDocument(Document):
    log_entry = models.ForeignKey('ApplicationLogEntry',related_name='documents')
    _file = models.FileField(upload_to=update_application_comms_log_filename)

    class Meta:
        app_label = 'wildlifecompliance'

class ApplicationLogEntry(CommunicationsLogEntry):
    application = models.ForeignKey(Application, related_name='comms_logs')

    class Meta:
        app_label = 'wildlifecompliance'

    def save(self, **kwargs):
        # save the application reference if the reference not provided
        if not self.reference:
            self.reference = self.application.reference
        super(ApplicationLogEntry, self).save(**kwargs)

class ApplicationRequest(models.Model):
    application = models.ForeignKey(Application)
    subject = models.CharField(max_length=200, blank=True)
    text = models.TextField(blank=True)
    officer = models.ForeignKey(EmailUser, null=True)

    class Meta:
        app_label = 'wildlifecompliance'

class ReturnRequest(ApplicationRequest):
    REASON_CHOICES = (('outstanding', 'There are currently outstanding returns for the previous licence'),
                      ('other', 'Other'))
    reason = models.CharField('Reason', max_length=30, choices=REASON_CHOICES, default=REASON_CHOICES[0][0])

    class Meta:
        app_label = 'wildlifecompliance'


class AmendmentRequest(ApplicationRequest):
    STATUS_CHOICES = (('requested', 'Requested'), ('amended', 'Amended'))
    REASON_CHOICES = (('insufficient_detail', 'The information provided was insufficient'),
                      ('missing_information', 'There was missing information'),
                      ('other', 'Other'))
    status = models.CharField('Status', max_length=30, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0])
    reason = models.CharField('Reason', max_length=30, choices=REASON_CHOICES, default=REASON_CHOICES[0][0])

    class Meta:
        app_label = 'wildlifecompliance'

class Assessment(ApplicationRequest):
    STATUS_CHOICES = (('awaiting_assessment', 'Awaiting Assessment'), ('assessed', 'Assessed'),
                      ('assessment_expired', 'Assessment Period Expired'))
    assigned_assessor = models.ForeignKey(EmailUser, blank=True, null=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0])
    date_last_reminded = models.DateField(null=True, blank=True)
    #conditions = models.ManyToManyField('Condition', through='AssessmentCondition')
    comment = models.TextField(blank=True)
    purpose = models.TextField(blank=True)

    class Meta:
        app_label = 'wildlifecompliance'

class ApplicationDeclinedDetails(models.Model):
    application = models.OneToOneField(Application)
    officer = models.ForeignKey(EmailUser, null=False)
    reason = models.TextField(blank=True)
    cc_email = models.TextField(null=True)

    class Meta:
        app_label = 'wildlifecompliance'

@python_2_unicode_compatible
class ApplicationStandardCondition(RevisionedMixin):
    text = models.TextField()
    code = models.CharField(max_length=10, unique=True)
    obsolete = models.BooleanField(default=False)

    def __str__(self):
        return self.code

    class Meta:
        app_label = 'wildlifecompliance'

class ApplicationCondition(OrderedModel):
    RECURRENCE_PATTERNS = [(1, 'Weekly'), (2, 'Monthly'), (3, 'Yearly')]
    standard_condition = models.ForeignKey(ApplicationStandardCondition,null=True,blank=True)
    free_condition = models.TextField(null=True,blank=True)
    standard = models.BooleanField(default=True)
    application = models.ForeignKey(Application,related_name='conditions')
    due_date = models.DateField(null=True,blank=True)
    recurrence = models.BooleanField(default=False)
    recurrence_pattern = models.SmallIntegerField(choices=RECURRENCE_PATTERNS,default=1)
    recurrence_schedule = models.IntegerField(null=True,blank=True)
    #order = models.IntegerField(default=1)

    class Meta:
        app_label = 'wildlifecompliance'


    @property
    def condition(self):
        return self.standard_condition.text if self.standard else self.free_condition

class ApplicationUserAction(UserAction):
    ACTION_CREATE_CUSTOMER_ = "Create customer {}"
    ACTION_CREATE_PROFILE_ = "Create profile {}"
    ACTION_LODGE_APPLICATION = "Lodge application {}"
    ACTION_ASSIGN_TO_ASSESSOR = "Assign application {} to {} as the assessor"
    ACTION_UNASSIGN_ASSESSOR = "Unassign assessor from application {}"
    ACTION_ASSIGN_TO_APPROVER = "Assign application {} to {} as the approver"
    ACTION_UNASSIGN_APPROVER = "Unassign approver from application {}"
    ACTION_ACCEPT_ID = "Accept ID"
    ACTION_RESET_ID = "Reset ID"
    ACTION_ID_REQUEST_UPDATE = 'Request ID update'
    ACTION_ACCEPT_CHARACTER = 'Accept character'
    ACTION_RESET_CHARACTER = "Reset character"
    ACTION_ACCEPT_REVIEW = 'Accept review'
    ACTION_RESET_REVIEW = "Reset review"
    ACTION_ID_REQUEST_AMENDMENTS = "Request amendments"
    ACTION_SEND_FOR_ASSESSMENT_TO_ = "Send for assessment to {}"
    ACTION_SEND_ASSESSMENT_REMINDER_TO_ = "Send assessment reminder to {}"
    ACTION_DECLINE = "Decline application {}"
    ACTION_ENTER_CONDITIONS = "Enter condition"
    ACTION_CREATE_CONDITION_ = "Create condition {}"
    ACTION_ISSUE_LICENCE_ = "Issue Licence for application {}"
    ACTION_DISCARD_application = "Discard application {}"
    # Assessors
    ACTION_SAVE_ASSESSMENT_ = "Save assessment {}"
    ACTION_CONCLUDE_ASSESSMENT_ = "Conclude assessment {}"
    ACTION_PROPOSED_LICENCE = "Application {} has been proposed for licence"
    ACTION_PROPOSED_DECLINE = "Application {} has been proposed for decline"
    # Referrals
    ACTION_SEND_REFERRAL_TO = "Send referral {} for application {} to {}"
    ACTION_RESEND_REFERRAL_TO = "Resend referral {} for application {} to {}"
    ACTION_REMIND_REFERRAL = "Send reminder for referral {} for application {} to {}"
    RECALL_REFERRAL = "Referral {} for application {} has been recalled"
    CONCLUDE_REFERRAL = "Referral {} for application {} has been concluded by {}"
    

    class Meta:
        app_label = 'wildlifecompliance'
        ordering = ('-when',)

    @classmethod
    def log_action(cls, application, action, user):
        return cls.objects.create(
            application=application,
            who=user,
            what=str(action)
        )

    application = models.ForeignKey(Application, related_name='action_logs')


class Referral(models.Model):
    SENT_CHOICES = (
        (1,'Sent From Assessor'),
        (2,'Sent From Referral')
    )
    PROCESSING_STATUS_CHOICES = (
                                 ('with_referral', 'Awaiting'),
                                 ('recalled', 'Recalled'),
                                 ('completed', 'Completed'),
                                 )
    lodged_on = models.DateTimeField(auto_now_add=True)
    application = models.ForeignKey(Application,related_name='referrals')
    sent_by = models.ForeignKey(EmailUser,related_name='wildlifecompliance_assessor_referrals')
    referral = models.ForeignKey(EmailUser,null=True,blank=True,related_name='wildlifecompliance_referalls')
    linked = models.BooleanField(default=False)
    sent_from = models.SmallIntegerField(choices=SENT_CHOICES,default=SENT_CHOICES[0][0])
    processing_status = models.CharField('Processing Status', max_length=30, choices=PROCESSING_STATUS_CHOICES,
                                         default=PROCESSING_STATUS_CHOICES[0][0]) 

    class Meta:
        app_label = 'wildlifecompliance'
        ordering = ('-lodged_on',)

    def __str__(self):
        return 'Application {} - Referral {}'.format(self.application.id,self.id)
    
    # Methods

    def recall(self,request):
        with transaction.atomic():
            if not self.application.can_assess(request.user):
                raise exceptions.ApplicationNotAuthorized() 
            self.processing_status = 'recalled'
            self.save()
            # TODO Log application action
            self.application.log_user_action(ApplicationUserAction.RECALL_REFERRAL.format(self.id,self.application.id),request)
            # TODO log organisation action
            self.application.applicant.log_user_action(ApplicationUserAction.RECALL_REFERRAL.format(self.id,self.application.id),request)

    def remind(self,request):
        with transaction.atomic():
            if not self.application.can_assess(request.user):
                raise exceptions.ApplicationNotAuthorized() 
            # Create a log entry for the application
            self.application.log_user_action(ApplicationUserAction.ACTION_REMIND_REFERRAL.format(self.id,self.application.id,'{}({})'.format(self.referral.get_full_name(),self.referral.email)),request)
            # Create a log entry for the organisation
            self.application.applicant.log_user_action(ApplicationUserAction.ACTION_REMIND_REFERRAL.format(self.id,self.application.id,'{}({})'.format(self.referral.get_full_name(),self.referral.email)),request)
            # send email
            send_referral_email_notification(self,request,reminder=True)

    def resend(self,request):
        with transaction.atomic():
            if not self.application.can_assess(request.user):
                raise exceptions.ApplicationNotAuthorized() 
            self.processing_status = 'with_referral'
            self.application.processing_status = 'with_referral'
            self.application.save()
            self.sent_from = 1
            self.save()
            # Create a log entry for the application
            self.application.log_user_action(ApplicationUserAction.ACTION_RESEND_REFERRAL_TO.format(self.id,self.application.id,'{}({})'.format(self.referral.get_full_name(),self.referral.email)),request)
            # Create a log entry for the organisation
            self.application.applicant.log_user_action(ApplicationUserAction.ACTION_RESEND_REFERRAL_TO.format(self.id,self.application.id,'{}({})'.format(self.referral.get_full_name(),self.referral.email)),request)
            # send email
            send_referral_email_notification(self,request)

    def complete(self,request):
        with transaction.atomic():
            try:
                if request.user != self.referral:
                    raise exceptions.ReferralNotAuthorized()
                self.processing_status = 'completed'
                self.save()
                # TODO Log application action
                self.application.log_user_action(ApplicationUserAction.CONCLUDE_REFERRAL.format(self.id,self.application.id,'{}({})'.format(self.referral.get_full_name(),self.referral.email)),request)
                # TODO log organisation action
                self.application.applicant.log_user_action(ApplicationUserAction.CONCLUDE_REFERRAL.format(self.id,self.application.id,'{}({})'.format(self.referral.get_full_name(),self.referral.email)),request)
            except:
                raise

    def send_referral(self,request,referral_email):
        with transaction.atomic():
            try:
                if self.application.processing_status == 'with_referral':
                    if request.user != self.referral:
                        raise exceptions.ReferralNotAuthorized()
                    if self.sent_from != 1:
                        raise exceptions.ReferralCanNotSend()
                    self.application.processing_status = 'with_referral'
                    self.application.save()
                    referral = None
                    # Check if the user is in ledger
                    try:
                        user = EmailUser.objects.get(email__icontains=referral_email)
                    except EmailUser.DoesNotExist:
                        # Validate if it is a deparment user
                        department_user = get_department_user(referral_email)
                        if not department_user:
                            raise ValidationError('The user you want to send the referral to is not a member of the department')
                        # Check if the user is in ledger or create
                        
                        user,created = EmailUser.objects.get_or_create(email=department_user['email'].lower())
                        if created:
                            user.first_name = department_user['given_name']
                            user.last_name = department_user['surname']
                            user.save()
                    try:
                        Referral.objects.get(referral=user,application=self.application)
                        raise ValidationError('A referral has already been sent to this user')
                    except Referral.DoesNotExist:
                        # Create Referral
                        referral = Referral.objects.create(
                            application = self.application,
                            referral=user,
                            sent_by=request.user,
                            sent_from=2
                        )
                    # Create a log entry for the application
                    self.application.log_user_action(ApplicationUserAction.ACTION_SEND_REFERRAL_TO.format(referral.id,self.id,'{}({})'.format(user.get_full_name(),user.email)),request)
                    # Create a log entry for the organisation
                    self.application.applicant.log_user_action(ApplicationUserAction.ACTION_SEND_REFERRAL_TO.format(referral.id,self.id,'{}({})'.format(user.get_full_name(),user.email)),request)
                    # send email
                    send_referral_email_notification(referral,request)
                else:
                    raise exceptions.ApplicationReferralCannotBeSent()
            except:
                raise

    # Properties
    @property
    def region(self):
        return self.application.region

    @property
    def activity(self):
        return self.application.activity

    @property
    def title(self):
        return self.application.title

    @property
    def applicant(self):
        return self.application.applicant.name

    @property
    def can_be_processed(self):
        return self.processing_status == 'with_referral'

    def can_assess_referral(self,user):
        return self.processing_status == 'with_referral'

@receiver(pre_delete, sender=Application)
def delete_documents(sender, instance, *args, **kwargs):
    for document in instance.documents.all():
        document.delete()
