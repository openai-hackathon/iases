import copy
import pytest
from fabops.domain import run


def test_transitive_closure():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}, {'id': 'b', 'revision': 1, 'content': 'b', 'requires': [['c', 1]], 'revoked': False, 'sha256': '3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d'}, {'id': 'c', 'revision': 1, 'content': 'c', 'requires': [], 'revoked': False, 'sha256': '2e7d2c03a9507ae265ecf5b5356885a53393a2029d241394997265a1a25aefc6'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed'], 'installed': [['c', 1, 'c'], ['b', 1, 'b'], ['a', 1, 'a']]}
    assert request == before

def test_diamond():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [['c', 1], ['b', 1]], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}, {'id': 'b', 'revision': 1, 'content': 'b', 'requires': [['d', 1]], 'revoked': False, 'sha256': '3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d'}, {'id': 'c', 'revision': 1, 'content': 'c', 'requires': [['d', 1]], 'revoked': False, 'sha256': '2e7d2c03a9507ae265ecf5b5356885a53393a2029d241394997265a1a25aefc6'}, {'id': 'd', 'revision': 1, 'content': 'd', 'requires': [], 'revoked': False, 'sha256': '18ac3e7343f016890c510e93f935261169d9e3f565436429830faf0934f4f8e4'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed'], 'installed': [['d', 1, 'd'], ['b', 1, 'b'], ['c', 1, 'c'], ['a', 1, 'a']]}
    assert request == before

def test_self_cycle():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [['a', 1]], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['invalid'], 'installed': []}
    assert request == before

def test_indirect_cycle():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}, {'id': 'b', 'revision': 1, 'content': 'b', 'requires': [['c', 1]], 'revoked': False, 'sha256': '3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d'}, {'id': 'c', 'revision': 1, 'content': 'c', 'requires': [['a', 1]], 'revoked': False, 'sha256': '2e7d2c03a9507ae265ecf5b5356885a53393a2029d241394997265a1a25aefc6'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['invalid'], 'installed': []}
    assert request == before

def test_incompatible_roots():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}, {'id': 'a', 'revision': 2, 'content': 'new', 'requires': [], 'revoked': False, 'sha256': '11507a0e2f5e69d5dfa40a62a1bd7b6ee57e6bcd85c67c9b8431b36fff21c437'}], 'commands': [{'op': 'install', 'roots': [['a', 1], ['a', 2]], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['invalid'], 'installed': []}
    assert request == before

def test_transitive_pin_conflict():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [['c', 1]], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}, {'id': 'b', 'revision': 1, 'content': 'b', 'requires': [['c', 2]], 'revoked': False, 'sha256': '3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d'}, {'id': 'c', 'revision': 1, 'content': 'c', 'requires': [], 'revoked': False, 'sha256': '2e7d2c03a9507ae265ecf5b5356885a53393a2029d241394997265a1a25aefc6'}, {'id': 'c', 'revision': 2, 'content': 'new', 'requires': [], 'revoked': False, 'sha256': '11507a0e2f5e69d5dfa40a62a1bd7b6ee57e6bcd85c67c9b8431b36fff21c437'}], 'commands': [{'op': 'install', 'roots': [['a', 1], ['b', 1]], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['invalid'], 'installed': []}
    assert request == before

def test_bad_leaf_digest():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}, {'id': 'b', 'revision': 1, 'content': 'b', 'requires': [], 'revoked': False, 'sha256': '0000000000000000000000000000000000000000000000000000000000000000'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['invalid'], 'installed': []}
    assert request == before

def test_missing_exact_revision():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [['b', 2]], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}, {'id': 'b', 'revision': 1, 'content': 'b', 'requires': [], 'revoked': False, 'sha256': '3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['invalid'], 'installed': []}
    assert request == before

def test_revoked_dependency():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}, {'id': 'b', 'revision': 1, 'content': 'b', 'requires': [], 'revoked': True, 'sha256': '3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['invalid'], 'installed': []}
    assert request == before

def test_unreachable_corruption():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}, {'id': 'bad', 'revision': 1, 'content': 'bad', 'requires': [['missing', 9]], 'revoked': False, 'sha256': '0000000000000000000000000000000000000000000000000000000000000000'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed', 'restarted'], 'installed': [['a', 1, 'a']]}
    assert request == before

def test_duplicate_shared_roots():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [['b', 1], ['b', 1]], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}, {'id': 'b', 'revision': 1, 'content': 'b', 'requires': [], 'revoked': False, 'sha256': '3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d'}], 'commands': [{'op': 'install', 'roots': [['b', 1], ['a', 1], ['a', 1]], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed'], 'installed': [['b', 1, 'b'], ['a', 1, 'a']]}
    assert request == before

def test_invalid_preserves_existing():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}, {'id': 'b', 'revision': 1, 'content': 'b', 'requires': [], 'revoked': False, 'sha256': '0000000000000000000000000000000000000000000000000000000000000000'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}, {'op': 'install', 'roots': [['b', 1]], 'crash': True}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed', 'invalid', 'restarted'], 'installed': [['a', 1, 'a']]}
    assert request == before

def test_retry_interrupted_replacement():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}, {'id': 'b', 'revision': 1, 'content': 'b', 'requires': [], 'revoked': False, 'sha256': '3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}, {'op': 'install', 'roots': [['b', 1]], 'crash': True}, {'op': 'restart'}, {'op': 'install', 'roots': [['b', 1]], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed', 'crashed', 'restarted', 'installed'], 'installed': [['b', 1, 'b']]}
    assert request == before

def test_empty_replacement():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}, {'op': 'install', 'roots': [], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed', 'installed'], 'installed': []}
    assert request == before

def test_failed_empty_replacement():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}, {'op': 'install', 'roots': [], 'crash': True}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed', 'crashed', 'restarted'], 'installed': [['a', 1, 'a']]}
    assert request == before

def test_unicode_content():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'μm\n', 'requires': [], 'revoked': False, 'sha256': 'c52c15764c6019210959e40dc2be9037d81b5102fa15fe00f574f00529ab35c1'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed'], 'installed': [['a', 1, 'μm\n']]}
    assert request == before

