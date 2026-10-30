from django.contrib import admin
from django.urls import path
from appstore import views
urlpatterns = [path('admin/', admin.site.urls), path('catalog.json', views.catalog), path('healthz', views.health)]
