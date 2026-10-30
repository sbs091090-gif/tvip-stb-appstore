import hashlib
import tempfile
import zipfile
from django.core.exceptions import ValidationError

MAX_APK_SIZE = 512 * 1024 * 1024


def inspect_apk(upload, expected_package):
    if upload.size > MAX_APK_SIZE:
        raise ValidationError('APK превышает 512 MiB.')
    digest = hashlib.sha256()
    with tempfile.NamedTemporaryFile(suffix='.apk') as temporary:
        for chunk in upload.chunks():
            digest.update(chunk)
            temporary.write(chunk)
        temporary.flush()
        try:
            with zipfile.ZipFile(temporary.name) as archive:
                manifests = [entry for entry in archive.infolist() if entry.filename == 'AndroidManifest.xml']
                if len(manifests) != 1 or manifests[0].file_size > 4 * 1024 * 1024:
                    raise ValueError('invalid manifest')
            from androguard.core.apk import APK
            from loguru import logger
            logger.disable('androguard')
            apk = APK(temporary.name)
            if not apk.is_valid_APK() or apk.get_package() != expected_package:
                raise ValueError('package mismatch or invalid APK')
            result = {'version_code': int(apk.get_androidversion_code()),
                      'version_name': apk.get_androidversion_name(),
                      'min_sdk': int(apk.get_min_sdk_version() or 1),
                      'sha256': digest.hexdigest(), 'size': upload.size, 'permissions': apk.get_permissions()}
            if not result['version_name'] or result['version_code'] < 1:
                raise ValueError('invalid version')
            return result
        except Exception as exc:
            raise ValidationError('Не удалось прочитать APK или package name не совпадает с приложением.') from exc
        finally:
            upload.seek(0)
