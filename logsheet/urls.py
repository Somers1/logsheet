from django.conf import settings
from django.contrib import admin
from django.urls import path
from project import views

urlpatterns = [
    path('timesheet/<int:pk>/<str:month>', views.ProjectTimesheetListView.as_view(), name='timesheet'),
]

if not settings.UNCHAINED:
    urlpatterns += [
        path("admin/", admin.site.urls),
    ]
