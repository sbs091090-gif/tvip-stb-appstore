from django.test import SimpleTestCase
from appstore.targeting import CatalogSnapshot


class TargetingTests(SimpleTestCase):
    def setUp(self):
        self.snapshot = CatalogSnapshot([
            {'package': 'tv.example', 'default': {'version': 1}, 'rules': [
                ('10.0.0.0/8', {'version': 2}),
                ('10.1.0.0/16', {'version': 3}),
                ('2001:db8::/32', {'version': 4}),
            ]},
        ])

    def test_default(self):
        self.assertEqual(self.snapshot.select('192.0.2.1')[0]['version'], 1)

    def test_longest_prefix(self):
        self.assertEqual(self.snapshot.select('10.1.2.3')[0]['version'], 3)
        self.assertEqual(self.snapshot.select('10.2.2.3')[0]['version'], 2)

    def test_ipv6(self):
        self.assertEqual(self.snapshot.select('2001:db8::1')[0]['version'], 4)

    def test_invalid_ip_fails_closed(self):
        with self.assertRaises(ValueError):
            self.snapshot.select('garbage')

    def test_snapshot_does_not_leak_mutation(self):
        self.snapshot.select('10.1.1.1')[0]['version'] = 99
        self.assertEqual(self.snapshot.select('10.1.1.1')[0]['version'], 3)

    def test_overlapping_rules_for_independent_apps(self):
        snapshot = CatalogSnapshot([
            {'package': 'a', 'default': {'package': 'a', 'version': 1},
             'rules': [('10.0.0.0/8', {'package': 'a', 'version': 2})]},
            {'package': 'b', 'default': {'package': 'b', 'version': 1},
             'rules': [('10.1.0.0/16', {'package': 'b', 'version': 3})]},
        ])
        self.assertEqual([app['version'] for app in snapshot.select('10.1.2.3')], [2, 3])

    def test_default_route_and_host_route(self):
        snapshot = CatalogSnapshot([{'package': 'a', 'default': {'version': 1}, 'rules': [
            ('0.0.0.0/0', {'version': 2}), ('192.0.2.1/32', {'version': 3}),
        ]}])
        self.assertEqual(snapshot.select('192.0.2.1')[0]['version'], 3)
        self.assertEqual(snapshot.select('192.0.2.2')[0]['version'], 2)
        self.assertEqual(snapshot.select('::1')[0]['version'], 1)
