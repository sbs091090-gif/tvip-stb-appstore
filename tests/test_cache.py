from django.test import TransactionTestCase
from appstore.models import Application, Release, TargetRule
from appstore import cache


class CacheTests(TransactionTestCase):
    def test_database_to_memory_and_disable(self):
        app = Application.objects.create(package_name='tv.test', title='Test')
        default = Release.objects.create(application=app, apk='assets/a.apk', version_code=1,
            version_name='1', min_sdk=19, sha256='0' * 64, size=3, is_default=True)
        beta = Release.objects.create(application=app, apk='assets/b.apk', version_code=2,
            version_name='2', min_sdk=19, sha256='1' * 64, size=4)
        TargetRule.objects.create(application=app, release=beta, cidr='10.0.0.0/8')
        cache.refresh()
        with self.assertNumQueries(0):
            snapshot = cache.current()
            self.assertEqual(snapshot.select('10.1.2.3')[0]['buildNumber'], 2)
            self.assertEqual(snapshot.select('192.0.2.1')[0]['buildNumber'], 1)
        app.enabled = False
        app.save()
        cache.refresh()
        self.assertEqual(cache.current().select('10.1.2.3'), [])
