from django.db import models
from django.utils import timezone
import uuid
import logging
from datetime import timedelta
from django.contrib.auth.models import User
from oauth2_provider.models import AccessToken, Application

from valhalla.proposals.models import Proposal

logger = logging.getLogger()


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    institution = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    notifications_enabled = models.BooleanField(default=False)
    simple_interface = models.BooleanField(default=False)

    @property
    def archive_bearer_token(self):
        # During testing, you will probably have to copy access tokens from prod for this to work
        try:
            app = Application.objects.get(name='Archive')
        except Application.DoesNotExist:
            logger.error('Archive application not found. Oauth applications need to be populated.')
            return ''
        access_token = AccessToken.objects.filter(user=self.user, application=app, expires__gt=timezone.now()).last()
        if not access_token:
            access_token = AccessToken(
                user=self.user,
                application=app,
                token=uuid.uuid4().hex,
                expires=timezone.now() + timedelta(days=30)
            )
            access_token.save()
        return access_token.token

    @property
    def current_proposals(self):
        return Proposal.current_proposals().filter(active=True, membership__user=self.user).distinct()

    def __str__(self):
        return '{0} {1} at {2}'.format(self.user, self.title, self.institution)
