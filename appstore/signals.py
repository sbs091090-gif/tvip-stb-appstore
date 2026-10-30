from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Application, Release, TargetRule, Screenshot, StoreSettings


@receiver(post_save)
@receiver(post_delete)
def changed(sender, **kwargs):
    if sender in (Application, Release, TargetRule, Screenshot):
        store, _ = StoreSettings.objects.get_or_create(pk=1)
        StoreSettings.objects.filter(pk=store.pk).update(modified=timezone.now())
