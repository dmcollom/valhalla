from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from django.template.loader import render_to_string
from django.contrib.staticfiles import finders
from weasyprint import HTML, CSS
from PyPDF2 import PdfFileMerger
import io

from valhalla.proposals.models import (
    Semester, TimeAllocation, Proposal, TimeAllocationGroup, Membership
)


class Instrument(models.Model):
    code = models.CharField(max_length=50)
    telescope_class = models.CharField(max_length=20, choices=TimeAllocation.TELESCOPE_CLASSES)
    display = models.CharField(max_length=50)

    def __str__(self):
        return self.display


class Call(models.Model):
    SCI_PROPOSAL = 'SCI'
    DDT_PROPOSAL = 'DDT'
    KEY_PROPOSAL = 'KEY'
    NAOC_PROPOSAL = 'NAOC'

    PROPOSAL_TYPE_CHOICES = (
        (SCI_PROPOSAL, 'Science'),
        (DDT_PROPOSAL, 'Director\'s Discretionary Time'),
        (KEY_PROPOSAL, 'Key Project'),
        (NAOC_PROPOSAL, 'NAOC proposal')
    )

    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    opens = models.DateTimeField()
    deadline = models.DateTimeField()
    call_url = models.URLField(blank=True, default='')
    instruments = models.ManyToManyField(Instrument)
    proposal_type = models.CharField(max_length=5, choices=PROPOSAL_TYPE_CHOICES)
    eligibility = models.TextField(blank=True, default='')
    eligibility_short = models.TextField(blank=True, default='')

    @classmethod
    def open_calls(cls):
        return cls.objects.filter(opens__lte=timezone.now(), deadline__gte=timezone.now())

    def __str__(self):
        return '{0} call for {1}'.format(self.get_proposal_type_display(), self.semester)


def pdf_upload_path(instance, filename):
    # PDFs will be uploaded to MEDIA_ROOT/sciapps/<semester>/
    return 'sciapps/{0}/{1}'.format(instance.call.semester.id, filename)


class ScienceApplication(models.Model):
    DRAFT = 'DRAFT'
    SUBMITTED = 'SUBMITTED'
    ACCEPTED = 'ACCEPTED'
    REJECTED = 'REJECTED'
    PORTED = 'PORTED'

    STATUS_CHOICES = (
        (DRAFT, 'Draft'),
        (SUBMITTED, 'Submitted'),
        (ACCEPTED, 'Accepted'),
        (REJECTED, 'Rejected'),
        (PORTED, 'Ported')
    )

    title = models.CharField(max_length=200)
    call = models.ForeignKey(Call, on_delete=models.CASCADE)
    submitter = models.ForeignKey(User, on_delete=models.CASCADE)
    abstract = models.TextField(blank=True, default='')
    pi = models.EmailField(blank=True, default='')
    pi_first_name = models.CharField(max_length=255, blank=True, default='', help_text='')
    pi_last_name = models.CharField(max_length=255, blank=True, default='', help_text='')
    pi_institution = models.CharField(max_length=255, blank=True, default='', help_text='')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0])
    proposal = models.ForeignKey(Proposal, null=True, blank=True, on_delete=models.SET_NULL)
    tac_rank = models.PositiveIntegerField(default=0)
    tac_priority = models.PositiveIntegerField(default=0)
    pdf = models.FileField(upload_to=pdf_upload_path, blank=True, null=True)

    # Admin only Notes
    notes = models.TextField(blank=True, default='', help_text='Add notes here. Not visible to users.')

    # Misc
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    submitted = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-id',)

    def __str__(self):
        return self.title

    @property
    def proposal_code(self):
        proposal_type_to_name = {
            'SCI': 'LCO',
            'KEY': 'KEY',
            'DDT': 'DDT',
            'NAOC': 'NAOC'
        }
        return '{0}{1}-{2}'.format(
            proposal_type_to_name[self.call.proposal_type], self.call.semester, str(self.tac_rank).zfill(3)
        )

    def get_absolute_url(self):
        return reverse('sciapplications:detail', args=(self.id,))

    def convert_to_proposal(self):
        # Create the objects we need
        proposal = Proposal.objects.create(
            id=self.proposal_code,
            title=self.title,
            abstract=self.abstract,
            tac_priority=self.tac_priority,
            tac_rank=self.tac_rank,
            active=False,
            tag=TimeAllocationGroup.objects.get_or_create(id='LCOGT')[0],
        )

        for tr in self.timerequest_set.filter(approved=True):
            TimeAllocation.objects.create(
                std_allocation=tr.std_time,
                too_allocation=tr.too_time,
                telescope_class=tr.instrument.telescope_class,
                instrument_name=tr.instrument.code,
                semester=tr.semester,
                proposal=proposal
            )

        # Send invitations if necessary
        if self.pi:
            proposal.add_users([self.pi], Membership.PI)
        else:
            Membership.objects.create(proposal=proposal, user=self.submitter, role=Membership.PI)

        proposal.add_users([coi.email for coi in self.coinvestigator_set.all()], Membership.CI)

        self.proposal = proposal
        self.status = ScienceApplication.PORTED
        self.save()
        return proposal

    def generate_pdf(self):
        context = {
            'object': self,
            'pdf': True
        }
        with open(finders.find('css/print.css')) as f:
            css = CSS(string=f.read())
        html_string = render_to_string('sciapplications/scienceapplication_detail.html', context)
        html = HTML(string=html_string)
        fileobj = io.BytesIO()
        html.write_pdf(fileobj, stylesheets=[css])
        merger = PdfFileMerger()
        merger.append(fileobj)
        if self.pdf:
            merger.append(self.pdf.file)
        merger.write(fileobj)
        pdf = fileobj.getvalue()
        fileobj.close()
        return pdf


class TimeRequest(models.Model):
    science_application = models.ForeignKey(ScienceApplication, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE)
    std_time = models.PositiveIntegerField(default=0)
    too_time = models.PositiveIntegerField(default=0)
    crt_time = models.PositiveIntegerField(default=0)
    approved = models.BooleanField(default=False)

    class Meta:
        ordering = ('semester',)

    def __str__(self):
        return '{} {} TimeRequest'.format(self.science_application, self.instrument)


class CoInvestigator(models.Model):
    science_application = models.ForeignKey(ScienceApplication, on_delete=models.CASCADE)
    email = models.EmailField()
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)

    def __str__(self):
        return '{0} {1} <{2}> ({3})'.format(self.first_name, self.last_name, self.email, self.institution)
