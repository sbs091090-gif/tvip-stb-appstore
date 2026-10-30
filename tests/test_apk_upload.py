"""Integration test invoked with APK_FIXTURE pointing to a known APK in Docker."""
import os
from unittest import skipUnless
from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from appstore.apk import inspect_apk


@skipUnless(os.environ.get('APK_FIXTURE'), 'External APK fixture not supplied')
class ApkExtractionTests(SimpleTestCase):
    def test_binary_manifest_metadata(self):
        with open(os.environ['APK_FIXTURE'], 'rb') as source:
            upload = SimpleUploadedFile('hello.apk', source.read())
        metadata = inspect_apk(upload, 'de.rhab.helloworld')
        self.assertEqual(metadata['version_code'], 1)
        self.assertEqual(metadata['version_name'], '1.0')
        self.assertEqual(metadata['min_sdk'], 21)
        self.assertGreater(metadata['size'], 0)
        self.assertEqual(len(metadata['sha256']), 64)

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from appstore.models import Application, Release
import tempfile


@skipUnless(os.environ.get('APK_FIXTURE'), 'External APK fixture not supplied')
class AdminUploadTests(TestCase):
    def test_authenticated_upload_extracts_metadata(self):
        user = get_user_model().objects.create_superuser('testadmin', 'test@example.com', 'test-only-password')
        self.client.force_login(user)
        app = Application.objects.create(package_name='de.rhab.helloworld', title='Hello')
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            with open(os.environ['APK_FIXTURE'], 'rb') as source:
                response = self.client.post('/admin/appstore/release/add/', {
                    'application': app.pk, 'apk': SimpleUploadedFile('hello.apk', source.read()),
                    'release_notes': '', 'is_default': 'on', 'enabled': 'on', '_save': 'Save',
                })
            self.assertEqual(response.status_code, 302)
            release = Release.objects.get(application=app)
            self.assertEqual(release.version_code, 1)
            self.assertEqual(release.version_name, '1.0')
            self.assertTrue(release.apk.storage.exists(release.apk.name))
