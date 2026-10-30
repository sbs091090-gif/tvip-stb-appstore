from django import forms
from django.contrib import admin
from .apk import inspect_apk
from .models import Application, Release, TargetRule, Screenshot


class ReleaseForm(forms.ModelForm):
    class Meta:
        model = Release
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        apk, application = cleaned.get('apk'), cleaned.get('application')
        if apk and application and ('apk' in self.changed_data or 'application' in self.changed_data or not self.instance.pk):
            metadata = inspect_apk(apk, application.package_name)
            for key, value in metadata.items():
                setattr(self.instance, key, value)
            if Release.objects.filter(application=application, version_code=metadata['version_code']).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('Эта версия уже загружена.')
        return cleaned


class ScreenshotInline(admin.TabularInline):
    model = Screenshot
    extra = 0


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['title', 'package_name', 'enabled']
    search_fields = ['title', 'package_name']
    inlines = [ScreenshotInline]


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    form = ReleaseForm
    list_display = ['application', 'version_name', 'version_code', 'is_default', 'enabled']
    list_filter = ['enabled', 'is_default', 'application']
    readonly_fields = ['version_code', 'version_name', 'min_sdk', 'sha256', 'size']


@admin.register(TargetRule)
class TargetRuleAdmin(admin.ModelAdmin):
    list_display = ['application', 'cidr', 'release', 'enabled']
    list_filter = ['application', 'enabled']

from .models import StoreSettings
admin.site.register(StoreSettings)
