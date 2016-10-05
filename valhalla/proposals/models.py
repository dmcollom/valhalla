import uuid
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.urls import reverse


class Semester(models.Model):
    id = models.CharField(primary_key=True, max_length=20)
    start = models.DateTimeField()
    end = models.DateTimeField()
    proposals = models.ManyToManyField("Proposal", through="TimeAllocation")

    def __str__(self):
        return self.id


class TimeAllocationGroup(models.Model):
    id = models.CharField(max_length=20, primary_key=True)

    def __str__(self):
        return self.id


class Proposal(models.Model):
    id = models.CharField(primary_key=True, max_length=255)
    active = models.BooleanField(default=True)
    title = models.CharField(max_length=255, default='', blank=True)
    abstract = models.TextField(default='', blank=True)
    tac_priority = models.PositiveIntegerField()
    tag = models.ForeignKey(TimeAllocationGroup)
    public = models.BooleanField(default=False)
    users = models.ManyToManyField(User, through='Membership')

    def __str__(self):
        return self.id


class TimeAllocation(models.Model):
    TELESCOPE_CLASSES = (
        ('2m0', '2m0'),
        ('1m0', '1m0'),
        ('0m8', '0m8'),
        ('0m4', '0m4'),
    )

    std_allocation = models.FloatField(default=0)
    std_time_used = models.FloatField(default=0)
    ipp_limit = models.FloatField(default=0)
    ipp_time_available = models.FloatField(default=0)
    too_allocation = models.FloatField(default=0)
    too_time_used = models.FloatField(default=0)
    semester = models.ForeignKey(Semester)
    proposal = models.ForeignKey(Proposal)
    telescope_class = models.CharField(max_length=20, choices=TELESCOPE_CLASSES)

    def __str__(self):
        return 'Timeallocation for {0}-{1}'.format(self.proposal, self.semester)


class Membership(models.Model):
    PI = 'PI'
    CI = 'CI'
    ROLE_CHOICES = (
        (PI, 'Pricipal Investigator'),
        (CI, 'Co-Investigator')
    )

    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=5, choices=ROLE_CHOICES)

    def __str__(self):
        return '{0} {1} of {2}'.format(self.user, self.role, self.proposal)


class ProposalInvite(models.Model):
    proposal = models.ForeignKey(Proposal)
    role = models.CharField(max_length=5, choices=Membership.ROLE_CHOICES)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    used = models.DateTimeField(null=True)

    def accept(self, user):
        membership = Membership.objects.create(
            proposal=self.proposal,
            role=self.role,
            user=user,
        )
        self.used = timezone.now()
        self.membership = membership
        self.save()

    def send_invitation(self, email):
        subject = _('You have been added to a proposal for observing at LCO.global')
        message = render_to_string(
            'proposals/invitation.txt',
            {
                'proposal': self.proposal,
                'url': '{}?ptoken={}'.format(reverse('registration_register'), self.token)
            }
        )

        send_mail(subject, message, 'portal@lco.glboal', [email])
