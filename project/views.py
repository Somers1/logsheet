from django.views.generic import DetailView

from project import models


class TimesheetDetailView(DetailView):
    model = models.Timesheet
    template_name = 'timesheet.html'
    context_object_name = 'timesheet'
