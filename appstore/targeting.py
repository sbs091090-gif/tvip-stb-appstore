"""Immutable binary radix trie; JSON and ETags are compiled before serving requests."""
import copy
import hashlib
import ipaddress
import json


class Node:
    __slots__ = ('children', 'overrides', 'compiled')
    def __init__(self):
        self.children = {}
        self.overrides = {}
        self.compiled = None


class CatalogSnapshot:
    def __init__(self, applications, last_update=0, operator=None):
        roots = {4: Node(), 6: Node()}
        defaults = {}
        for application in applications:
            package = application['package']
            if application['default'] is not None:
                defaults[package] = application['default']
            for cidr, release in application['rules']:
                network = ipaddress.ip_network(cidr, strict=True)
                node = roots[network.version]
                bits = network.max_prefixlen
                number = int(network.network_address)
                for shift in range(bits - 1, bits - network.prefixlen - 1, -1):
                    node = node.children.setdefault((number >> shift) & 1, Node())
                node.overrides[package] = release
        self._roots = roots
        interned = {}
        def compile_node(node, inherited):
            selected = {**inherited, **node.overrides}
            document = {'protoVersion': 1, 'lastUpdate': last_update,
                        'updateCheckPeriodSec': 3600, 'operator': operator or {'name': 'TVIP Appstore'},
                        'apps': [selected[key] for key in sorted(selected)]}
            body = json.dumps(document, ensure_ascii=False, separators=(',', ':')).encode()
            etag = '"' + hashlib.sha256(body).hexdigest() + '"'
            node.compiled = interned.setdefault(etag, (body, etag))
            for child in node.children.values():
                compile_node(child, selected)
        for root in roots.values():
            compile_node(root, defaults)

    def response(self, address):
        address = ipaddress.ip_address(address)
        node = self._roots[address.version]
        number = int(address)
        for shift in range(address.max_prefixlen - 1, -1, -1):
            child = node.children.get((number >> shift) & 1)
            if child is None:
                break
            node = child
        return node.compiled

    def select(self, address):
        return copy.deepcopy(json.loads(self.response(address)[0])['apps'])
