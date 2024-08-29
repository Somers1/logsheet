from django.conf import settings
from django.contrib import admin
from django.urls import path
from project import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('timesheet/<int:pk>/<str:month>', views.ProjectTimesheetListView.as_view(), name='timesheet'),

]

if not settings.UNCHAINED:
    urlpatterns += [
        path("admin/", admin.site.urls),
    ]
