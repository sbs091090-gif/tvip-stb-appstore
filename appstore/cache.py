import hashlib
import json
import logging
import threading
import time
from django.conf import settings
from django.db import close_old_connections, transaction
from .targeting import CatalogSnapshot

logger = logging.getLogger(__name__)
_snapshot = None
_signature = None
_thread = None
_lock = threading.Lock()


class Unavailable(Exception):
    pass


def refresh():
    global _snapshot, _signature
    from .models import Application, StoreSettings
    with transaction.atomic():
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        apps = list(Application.objects.filter(enabled=True).prefetch_related('releases', 'rules__release', 'screenshots'))
        store = StoreSettings.objects.first()
        operator = {'name': store.name if store else 'TVIP Appstore'}
        if store:
            for key, field in [('logoUrl', store.logo), ('background', store.background)]:
                if field:
                    operator[key] = settings.PUBLIC_BASE_URL + field.url
        records = []
        timestamps = [int(store.modified.timestamp())] if store else [0]
        for app in apps:
            timestamps.append(int(app.modified.timestamp()))
            def serialize(release):
                return {'package': app.package_name, 'version': release.version_name,
                        'buildNumber': release.version_code, 'title': app.title, 'description': app.description,
                        'developer': app.developer, 'releaseNotes': release.release_notes,
                        'apkUrl': settings.PUBLIC_BASE_URL + release.apk.url, 'apkSize': release.size,
                        'ageRating': app.age_rating, 'categoriesTags': app.categories,
                        'customerRating': float(app.customer_rating), 'downloadCount': app.download_count,
                        'permissions': release.permissions,
                        'firstPublishDate': int(app.created.timestamp()), 'lastPublishDate': int(release.created.timestamp()),
                        'media': {'logoUrl': settings.PUBLIC_BASE_URL + app.icon.url if app.icon else '',
                                  'bannerUrl': settings.PUBLIC_BASE_URL + app.banner.url if app.banner else '',
                                  'screenshots': [settings.PUBLIC_BASE_URL + item.image.url for item in app.screenshots.all()]},
                        'rules': {'forceInstall': app.force_install, 'forceUpdate': app.force_update,
                                  'forceUninstall': app.force_uninstall}}
            releases = {release.pk: release for release in app.releases.all() if release.enabled}
            default = next((release for release in releases.values() if release.is_default), None)
            records.append({'package': app.package_name, 'default': serialize(default) if default else None,
                            'rules': [(rule.cidr, serialize(releases[rule.release_id])) for rule in app.rules.all()
                                      if rule.enabled and rule.release_id in releases]})
            timestamps.extend(int(release.modified.timestamp()) for release in releases.values())
        signature = hashlib.sha256(json.dumps([records, operator], sort_keys=True).encode()).hexdigest()
        if signature != _signature:
            # Deletions and rule edits also advance lastUpdate.
            stamp = max(timestamps)
            compiled = CatalogSnapshot(records, last_update=stamp, operator=operator)
            _snapshot, _signature = compiled, signature


def _poll():
    while True:
        try:
            close_old_connections()
            refresh()
        except Exception:
            logger.exception('Catalog refresh failed; retaining previous snapshot')
        finally:
            close_old_connections()
        time.sleep(settings.CATALOG_REFRESH_SECONDS)


def start():
    global _thread
    with _lock:
        if _thread is None:
            _thread = threading.Thread(target=_poll, name='catalog-refresh', daemon=True)
            _thread.start()


def current():
    if _snapshot is None:
        raise Unavailable()
    return _snapshot
