from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from appstore.models import Application, Release, TargetRule
from appstore.apk import inspect_apk
from appstore import cache


class PersistenceTests(TestCase):
    def setUp(self):
        self.app = Application.objects.create(package_name='tv.test', title='Test')
        self.release = Release.objects.create(application=self.app, apk='assets/test.apk', version_code=1,
            version_name='1.0', min_sdk=19, sha256='0' * 64, size=3, is_default=True)

    def test_duplicate_default_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Release.objects.create(application=self.app, apk='a.apk', version_code=2,
                version_name='2', min_sdk=19, sha256='0' * 64, size=1, is_default=True)

    def test_rule_cross_application_rejected(self):
        other = Application.objects.create(package_name='tv.other', title='Other')
        with self.assertRaises(ValidationError):
            TargetRule(application=other, release=self.release, cidr='10.0.0.0/8').full_clean()

    def test_invalid_network_rejected(self):
        with self.assertRaises(ValidationError):
            TargetRule(application=self.app, release=self.release, cidr='10.1.1.1/8').full_clean()

    def test_invalid_apk_rejected(self):
        with self.assertRaises(ValidationError):
            inspect_apk(SimpleUploadedFile('bad.apk', b'not a zip'), 'tv.test')

    def test_admin_requires_authentication(self):
        self.assertEqual(self.client.get('/admin/').status_code, 302)
