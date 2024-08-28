from django.contrib import admin
from . import models


class SourceRuleInLine(admin.TabularInline):
    model = models.SourceRule
    extra = 1


@admin.register(models.Source)
class SourceAdmin(admin.ModelAdmin):
    inlines = [SourceRuleInLine]


admin.site.register(models.Project)
admin.site.register(models.Event)
