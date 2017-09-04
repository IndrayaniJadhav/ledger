from django.http import HttpResponse,JsonResponse
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View, TemplateView
from disturbance.utils import create_data_from_form
from disturbance.components.proposals.models import Proposal
import json,traceback

class ProposalView(TemplateView):
    template_name = 'disturbance/proposal.html'

    def post(self, request, *args, **kwargs):
        extracted_fields = []
        try:
            proposal_id = request.POST.pop('proposal_id')
            proposal = Proposal.objects.get(proposal_id)
            schema = json.loads(request.POST.pop('schema')[0])
            extracted_fields = create_data_from_form(schema,request.POST, request.FILES)
            proposal.schema = schema;
            proposal.data = extracted_fields
            proposal.save()
            return redirect(reverse('external'))
        except:
            traceback.print_exc
            return JsonResponse({error:"someting went wrong"},safe=False,status=400)
