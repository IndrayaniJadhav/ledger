from django.contrib import admin

# Register your models here.
from . import models

@admin.register(models.CashTransaction)
class CashAdmin(admin.ModelAdmin):
    list_display = (
        'invoice',
        'amount',
        'type',
        'source',
        'region',
        'district',
        'created'
    )
    search_fields = [
        'invoice__reference',
        'type',
        'source',
        'region',
        'district',
    ]

@admin.register(models.Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    pass

@admin.register(models.InvoiceBPAY)
class InvoiceBpayAdmin(admin.ModelAdmin):
    pass

@admin.register(models.BpayTransaction)
class BpayTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'crn',
        'type',
        'txn_ref',
        'amount',
        'file',
        'p_date'
    )

@admin.register(models.BpayFile)
class BpayFileAdmin(admin.ModelAdmin):
    list_display = (
        #'creation_date',
        #'creation_time',
        'created',
    )

class BillerCodeRecipientInline(admin.StackedInline):
    model = models.BillerCodeRecipient
    extra = 1

@admin.register(models.BillerCodeSystem)
class BillerCodeSystemAdmin(admin.ModelAdmin):
    list_display= (
        'system',
        'biller_code'
    )
    inlines = [BillerCodeRecipientInline]

@admin.register(models.BpointTransaction)
class BpointTransactionAdmin(admin.ModelAdmin):
    readonly_fields = (
                        'action',
                        'amount',
                        'amount_original',
                        'amount_surcharge',
                        'cardtype',
                        'crn1',
                        'txn_number',
                        'original_txn',
                        'receipt_number',
                        'type',
                        'response_code',
                        'response_txt',
                        'processed',
                        'settlement_date',
                    )
    list_display = ('txn_number','receipt_number','action','amount','approved')
    
    def approved(self,obj):
        if obj.approved:
            return True
        return False
    approved.boolean = True
    
    def has_add_permission(self,request,obj=None):
        return False