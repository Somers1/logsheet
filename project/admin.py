from django.contrib import admin
from . import models

admin.site.register(models.Project)
admin.site.register(models.Source)
admin.site.register(models.Event)
admin.site.register(models.Timesheet)
