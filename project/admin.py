from django.contrib import admin
from . import models


class TimeSheetDayInline(admin.TabularInline):
    model = models.TimesheetDay
    extra = 1
    ordering = ('date',)


@admin.register(models.Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = ('project', 'start_time', 'end_time')
    list_filter = ('project', 'start_time', 'end_time')
    search_fields = ('project__name',)
    inlines = [TimeSheetDayInline]





admin.site.register(models.Project)
admin.site.register(models.Source)
admin.site.register(models.Event)
