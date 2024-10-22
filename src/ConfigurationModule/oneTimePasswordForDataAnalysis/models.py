from django.db import models
from django.utils import timezone
from datetime import timedelta
import secrets
import string

class OTP(models.Model):
    otp = models.CharField(max_length=6, unique = True)
    mongo_studio_id = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.used and self.expires_at > timezone.now()

    def mark_as_used(self):
        self.used = True
        self.save()

    @classmethod
    def generate_otp(cls, mongo_studio_id):
        characters = string.ascii_uppercase + string.digits
        otp_value = ''.join(secrets.choice(characters) for _ in range(6))
        expiration_time = timezone.now() + timedelta(hours=48)
        return cls.objects.create(otp=otp_value, mongo_studio_id=mongo_studio_id, expires_at=expiration_time)
