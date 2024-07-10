from django.db import models

class Interviewer(models.Model):
    interviewerName = models.CharField(max_length=100)
    interviewerProfilePicture = models.ImageField()
    interviewerTone = models.CharField(max_length=100)
    interviewerGreeting = models.CharField(max_length=100)
    surveyId = models.SmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.interviewerName

