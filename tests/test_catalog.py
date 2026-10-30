from django.test import SimpleTestCase, RequestFactory
from unittest.mock import patch
from appstore.targeting import CatalogSnapshot
from appstore.views import catalog


class CatalogTests(SimpleTestCase):
    def test_protocol_and_conditional_get(self):
        snapshot = CatalogSnapshot([{'package': 'a', 'default': {'package': 'a', 'buildNumber': 1}, 'rules': []}], last_update=123)
        with patch('appstore.views.cache.current', return_value=snapshot):
            request = RequestFactory().get('/catalog.json', HTTP_X_REAL_IP='192.0.2.1')
            response = catalog(request)
            import json
            document = json.loads(response.content)
            self.assertEqual(document['protoVersion'], 1)
            self.assertEqual(document['lastUpdate'], 123)
            self.assertEqual(document['apps'][0]['buildNumber'], 1)
            request.META['HTTP_IF_NONE_MATCH'] = response['ETag']
            self.assertEqual(catalog(request).status_code, 304)

    def test_variant_etags_are_distinct(self):
        snapshot = CatalogSnapshot([{'package': 'a', 'default': {'buildNumber': 1}, 'rules': [('10.0.0.0/8', {'buildNumber': 2})]}])
        self.assertNotEqual(snapshot.response('10.0.0.1')[1], snapshot.response('192.0.2.1')[1])

    def test_missing_real_ip(self):
        self.assertEqual(catalog(RequestFactory().get('/catalog.json')).status_code, 400)

    def test_weak_etag_and_head(self):
        snapshot = CatalogSnapshot([])
        with patch('appstore.views.cache.current', return_value=snapshot):
            factory = RequestFactory()
            response = catalog(factory.head('/catalog.json', HTTP_X_REAL_IP='::1'))
            self.assertEqual(response.content, b'')
            conditional = factory.get('/catalog.json', HTTP_X_REAL_IP='::1', HTTP_IF_NONE_MATCH='W/' + response['ETag'])
            self.assertEqual(catalog(conditional).status_code, 304)

    def test_only_safe_methods(self):
        self.assertEqual(catalog(RequestFactory().post('/catalog.json')).status_code, 405)

    def test_warming_catalog_returns_unavailable(self):
        from appstore.cache import Unavailable
        with patch('appstore.views.cache.current', side_effect=Unavailable):
            self.assertEqual(catalog(RequestFactory().get('/catalog.json', HTTP_X_REAL_IP='::1')).status_code, 503)
