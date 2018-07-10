from django.contrib import admin
from ledger.accounts.models import EmailUser
from wildlifecompliance.components.applications import models
from wildlifecompliance.components.applications import forms 
from reversion.admin import VersionAdmin
# Register your models here.

# @admin.register(models.ApplicationType)
# class ApplicationTypeAdmin(admin.ModelAdmin):
#     exclude=("site",) 

class ApplicationDocumentInline(admin.TabularInline):
    model = models.ApplicationDocument
    extra = 0

@admin.register(models.ApplicationType)
class ApplicationTypeAdmin(admin.ModelAdmin):
    pass

@admin.register(models.Application)
class ApplicationAdmin(VersionAdmin):
    inlines =[ApplicationDocumentInline,] 

@admin.register(models.ApplicationAssessorGroup)
class ApplicationAssessorGroupAdmin(admin.ModelAdmin):
    list_display = ['name','default']
    filter_horizontal = ('members',)
    form = forms.ApplicationAssessorGroupAdminForm
    readonly_fields = ['default']

    def has_delete_permission(self, request, obj=None):
        if obj and obj.default:
            return False
        return super(ApplicationAssessorGroupAdmin, self).has_delete_permission(request, obj)

@admin.register(models.ApplicationApproverGroup)
class ApplicationApproverGroupAdmin(admin.ModelAdmin):
    list_display = ['name','default']
    filter_horizontal = ('members',)
    form = forms.ApplicationApproverGroupAdminForm
    readonly_fields = ['default']

    def has_delete_permission(self, request, obj=None):
        if obj and obj.default:
            return False
        return super(ApplicationApproverGroupAdmin, self).has_delete_permission(request, obj)

@admin.register(models.ApplicationStandardCondition)
class ApplicationStandardConditionAdmin(admin.ModelAdmin):
    list_display = ['code','text','obsolete']
