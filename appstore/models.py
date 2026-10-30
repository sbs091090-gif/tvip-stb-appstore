import ipaddress
import uuid
from pathlib import Path
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models


def asset_path(instance, filename):
    return f'assets/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


def validate_cidr(value):
    try:
        ipaddress.ip_network(value, strict=True)
    except ValueError as exc:
        raise ValidationError('Укажите адрес сети в формате CIDR.') from exc


class Application(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    developer = models.CharField(max_length=255, blank=True)
    categories = models.JSONField(default=list, blank=True)
    age_rating = models.PositiveSmallIntegerField(default=0)
    customer_rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    download_count = models.PositiveBigIntegerField(default=0)
    force_install = models.BooleanField(default=False)
    force_update = models.BooleanField(default=False)
    force_uninstall = models.BooleanField(default=False)
    package_name = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    icon = models.ImageField(upload_to=asset_path, blank=True)
    banner = models.ImageField(upload_to=asset_path, blank=True)

    def clean(self):
        if self.banner:
            from PIL import Image
            image = Image.open(self.banner)
            if image.width * 9 != image.height * 16:
                raise ValidationError({'banner': 'Баннер должен иметь соотношение сторон 16:9.'})
            self.banner.seek(0)

    def __str__(self):
        return self.title


class Release(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    release_notes = models.TextField(blank=True)
    permissions = models.JSONField(default=list, blank=True, editable=False)
    application = models.ForeignKey(Application, related_name='releases', on_delete=models.CASCADE)
    apk = models.FileField(upload_to=asset_path, validators=[FileExtensionValidator(['apk'])])
    version_code = models.PositiveBigIntegerField(editable=False)
    version_name = models.CharField(max_length=255, editable=False)
    min_sdk = models.PositiveIntegerField(editable=False)
    sha256 = models.CharField(max_length=64, editable=False)
    size = models.PositiveBigIntegerField(editable=False)
    is_default = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['application', 'version_code'], name='unique_application_version'),
            models.UniqueConstraint(fields=['application'], condition=models.Q(is_default=True), name='one_default_release'),
        ]

    def __str__(self):
        return f'{self.application}: {self.version_name} ({self.version_code})'


class TargetRule(models.Model):
    application = models.ForeignKey(Application, related_name='rules', on_delete=models.CASCADE)
    release = models.ForeignKey(Release, on_delete=models.CASCADE)
    cidr = models.CharField(max_length=43, validators=[validate_cidr])
    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['application', 'cidr'], name='unique_application_cidr')]

    def clean(self):
        if self.release_id and self.application_id and self.release.application_id != self.application_id:
            raise ValidationError({'release': 'Версия должна принадлежать выбранному приложению.'})


class Screenshot(models.Model):
    application = models.ForeignKey(Application, related_name='screenshots', on_delete=models.CASCADE)
    image = models.ImageField(upload_to=asset_path)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'pk']


class StoreSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    name = models.CharField(max_length=255, default='TVIP Appstore')
    logo = models.ImageField(upload_to=asset_path, blank=True)
    background = models.ImageField(upload_to=asset_path, blank=True)
    modified = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        return super().save(*args, **kwargs)
