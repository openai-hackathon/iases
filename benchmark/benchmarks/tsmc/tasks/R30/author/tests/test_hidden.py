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

def test_prepared_crash_retry():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [['b', 2]], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}, {'id': 'b', 'revision': 1, 'content': 'b1', 'requires': [], 'revoked': False, 'sha256': '7dc96f776c8423e57a2785489a3f9c43fb6e756876d6ad9a9cac4aa4e72ec193'}, {'id': 'b', 'revision': 2, 'content': 'b2', 'requires': [], 'revoked': False, 'sha256': '4814d92093ac8a0f4a2163ab87dee509ba306a58f5888be0edcb2fcd0712028b'}], 'commands': [{'op': 'prepare', 'roots': [['a', 1]], 'id': 'p'}, {'op': 'commit', 'id': 'p', 'crash': True}, {'op': 'restart'}, {'op': 'commit', 'id': 'p'}, {'op': 'commit', 'id': 'p'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['prepared', 'crashed', 'restarted', 'installed', 'installed'], 'installed': [['b', 1, 'b1'], ['a', 1, 'a1']]}
    assert request == before

def test_empty_publication_stales_ticket_across_restart():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [['b', 2]], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}, {'id': 'b', 'revision': 1, 'content': 'b1', 'requires': [], 'revoked': False, 'sha256': '7dc96f776c8423e57a2785489a3f9c43fb6e756876d6ad9a9cac4aa4e72ec193'}, {'id': 'b', 'revision': 2, 'content': 'b2', 'requires': [], 'revoked': False, 'sha256': '4814d92093ac8a0f4a2163ab87dee509ba306a58f5888be0edcb2fcd0712028b'}], 'commands': [{'op': 'prepare', 'roots': [['a', 1]], 'id': 'p'}, {'op': 'install', 'roots': []}, {'op': 'restart'}, {'op': 'commit', 'id': 'p', 'crash': True}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['prepared', 'installed', 'restarted', 'stale'], 'installed': []}
    assert request == before

def test_floor_survives_empty_install():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [['b', 2]], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}, {'id': 'b', 'revision': 1, 'content': 'b1', 'requires': [], 'revoked': False, 'sha256': '7dc96f776c8423e57a2785489a3f9c43fb6e756876d6ad9a9cac4aa4e72ec193'}, {'id': 'b', 'revision': 2, 'content': 'b2', 'requires': [], 'revoked': False, 'sha256': '4814d92093ac8a0f4a2163ab87dee509ba306a58f5888be0edcb2fcd0712028b'}], 'commands': [{'op': 'install', 'roots': [['b', 2]]}, {'op': 'install', 'roots': []}, {'op': 'restart'}, {'op': 'install', 'roots': [['b', 1]]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed', 'installed', 'restarted', 'invalid'], 'installed': []}
    assert request == before

def test_dependency_floor():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [['b', 2]], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}, {'id': 'b', 'revision': 1, 'content': 'b1', 'requires': [], 'revoked': False, 'sha256': '7dc96f776c8423e57a2785489a3f9c43fb6e756876d6ad9a9cac4aa4e72ec193'}, {'id': 'b', 'revision': 2, 'content': 'b2', 'requires': [], 'revoked': False, 'sha256': '4814d92093ac8a0f4a2163ab87dee509ba306a58f5888be0edcb2fcd0712028b'}], 'commands': [{'op': 'install', 'roots': [['b', 2]]}, {'op': 'install', 'roots': [['a', 1]]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed', 'invalid'], 'installed': [['b', 2, 'b2']]}
    assert request == before

def test_prepare_does_not_raise_floor():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [['b', 2]], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}, {'id': 'b', 'revision': 1, 'content': 'b1', 'requires': [], 'revoked': False, 'sha256': '7dc96f776c8423e57a2785489a3f9c43fb6e756876d6ad9a9cac4aa4e72ec193'}, {'id': 'b', 'revision': 2, 'content': 'b2', 'requires': [], 'revoked': False, 'sha256': '4814d92093ac8a0f4a2163ab87dee509ba306a58f5888be0edcb2fcd0712028b'}], 'commands': [{'op': 'prepare', 'roots': [['b', 2]], 'id': 'p'}, {'op': 'install', 'roots': [['b', 1]]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['prepared', 'installed'], 'installed': [['b', 1, 'b1']]}
    assert request == before

def test_prepare_crash_leaves_no_ticket():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [['b', 2]], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}, {'id': 'b', 'revision': 1, 'content': 'b1', 'requires': [], 'revoked': False, 'sha256': '7dc96f776c8423e57a2785489a3f9c43fb6e756876d6ad9a9cac4aa4e72ec193'}, {'id': 'b', 'revision': 2, 'content': 'b2', 'requires': [], 'revoked': False, 'sha256': '4814d92093ac8a0f4a2163ab87dee509ba306a58f5888be0edcb2fcd0712028b'}], 'commands': [{'op': 'prepare', 'roots': [['a', 1]], 'id': 'p', 'crash': True}, {'op': 'restart'}, {'op': 'commit', 'id': 'p'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['crashed', 'restarted', 'missing'], 'installed': []}
    assert request == before

def test_ticket_root_conflict():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [['b', 2]], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}, {'id': 'b', 'revision': 1, 'content': 'b1', 'requires': [], 'revoked': False, 'sha256': '7dc96f776c8423e57a2785489a3f9c43fb6e756876d6ad9a9cac4aa4e72ec193'}, {'id': 'b', 'revision': 2, 'content': 'b2', 'requires': [], 'revoked': False, 'sha256': '4814d92093ac8a0f4a2163ab87dee509ba306a58f5888be0edcb2fcd0712028b'}], 'commands': [{'op': 'prepare', 'roots': [['a', 1]], 'id': 'p'}, {'op': 'prepare', 'roots': [['a', 2]], 'id': 'p'}, {'op': 'commit', 'id': 'p'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['prepared', 'conflict', 'installed'], 'installed': [['b', 1, 'b1'], ['a', 1, 'a1']]}
    assert request == before

def test_ticket_duplicate_roots():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [['b', 2]], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}, {'id': 'b', 'revision': 1, 'content': 'b1', 'requires': [], 'revoked': False, 'sha256': '7dc96f776c8423e57a2785489a3f9c43fb6e756876d6ad9a9cac4aa4e72ec193'}, {'id': 'b', 'revision': 2, 'content': 'b2', 'requires': [], 'revoked': False, 'sha256': '4814d92093ac8a0f4a2163ab87dee509ba306a58f5888be0edcb2fcd0712028b'}], 'commands': [{'op': 'prepare', 'roots': [['a', 1]], 'id': 'p'}, {'op': 'prepare', 'roots': [['a', 1], ['a', 1]], 'id': 'p'}, {'op': 'commit', 'id': 'p'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['prepared', 'prepared', 'installed'], 'installed': [['b', 1, 'b1'], ['a', 1, 'a1']]}
    assert request == before

def test_bad_high_revision_falls_back():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [], 'revoked': False, 'sha256': '0000000000000000000000000000000000000000000000000000000000000000'}], 'commands': [{'op': 'install', 'roots': [['a', 1, 2]]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed'], 'installed': [['a', 1, 'a1']]}
    assert request == before

def test_cyclic_high_revision_falls_back():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [['a', 2]], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}], 'commands': [{'op': 'install', 'roots': [['a', 1, 2]]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed'], 'installed': [['a', 1, 'a1']]}
    assert request == before

def test_range_upper_bound():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}, {'id': 'a', 'revision': 3, 'content': 'a3', 'requires': [], 'revoked': False, 'sha256': 'f46dd28a5499d8efef0b8fb8ee1ec1c5a5e407c9381741d576ba8deb4f59ec3f'}], 'commands': [{'op': 'install', 'roots': [['a', 1, 2]]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed'], 'installed': [['a', 2, 'a2']]}
    assert request == before

def test_crash_floor_rolls_back():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [['b', 2]], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}, {'id': 'b', 'revision': 1, 'content': 'b1', 'requires': [], 'revoked': False, 'sha256': '7dc96f776c8423e57a2785489a3f9c43fb6e756876d6ad9a9cac4aa4e72ec193'}, {'id': 'b', 'revision': 2, 'content': 'b2', 'requires': [], 'revoked': False, 'sha256': '4814d92093ac8a0f4a2163ab87dee509ba306a58f5888be0edcb2fcd0712028b'}], 'commands': [{'op': 'install', 'roots': [['b', 2]], 'crash': True}, {'op': 'restart'}, {'op': 'install', 'roots': [['b', 1]]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['crashed', 'restarted', 'installed'], 'installed': [['b', 1, 'b1']]}
    assert request == before

def test_global_revision_vector_beats_root_greed():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}, {'id': 'z', 'revision': 1, 'content': 'z1', 'requires': [['a', 2]], 'revoked': False, 'sha256': '44ba554e17977b31413d531e0aa4e02e87a7a38115d3be3b33c95f85fac2a4f7'}, {'id': 'z', 'revision': 2, 'content': 'z2', 'requires': [['a', 1]], 'revoked': False, 'sha256': '3c417b7ea567c3115deebed7319de56c4d008e6990b0d45ed5cfa53d4c5d37fa'}], 'commands': [{'op': 'install', 'roots': [['z', 1, 2]]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed'], 'installed': [['a', 2, 'a2'], ['z', 1, 'z1']]}
    assert request == before

def test_twelve_independent_ranges():
    request = {'artifacts': [{'id': 'p00', 'revision': 1, 'content': 'p001', 'requires': [], 'revoked': False, 'sha256': '476add61ae307328cfb24a7b4792945879aa610028d48378e4a85021e9214647'}, {'id': 'p00', 'revision': 2, 'content': 'p002', 'requires': [], 'revoked': False, 'sha256': 'fca5855dd15c06fe63155be37a8a782ad034198068d2ec66cf0c38f194fa5d5e'}, {'id': 'p00', 'revision': 3, 'content': 'p003', 'requires': [], 'revoked': False, 'sha256': '77092275327207a576bf6e8c84708ccaf1164fac719ad0408b3c9ab72501ffb8'}, {'id': 'p01', 'revision': 1, 'content': 'p011', 'requires': [], 'revoked': False, 'sha256': '0abe56f2a609e8d9bf6cd279f542ed40402ea0f1f9eace9938c8b46f41899a0a'}, {'id': 'p01', 'revision': 2, 'content': 'p012', 'requires': [], 'revoked': False, 'sha256': 'eb7eab272bbebf37e2e0f62346aadf522098f02291864f10b9e7797ffdf414e8'}, {'id': 'p01', 'revision': 3, 'content': 'p013', 'requires': [], 'revoked': False, 'sha256': '7158d711ad769fe8f31b12ab1fbd99081c76777f7b386c84bf39072ede407308'}, {'id': 'p02', 'revision': 1, 'content': 'p021', 'requires': [], 'revoked': False, 'sha256': '3878cd6735fb6d78a0d8a0e53d1f2273df6f7b8e550e645850880977fc637bb2'}, {'id': 'p02', 'revision': 2, 'content': 'p022', 'requires': [], 'revoked': False, 'sha256': 'f53265464b41646e5ce47cce7c15dd45dc4bc0dbe4611e328b720d5599a0ae7c'}, {'id': 'p02', 'revision': 3, 'content': 'p023', 'requires': [], 'revoked': False, 'sha256': '881a49cbef45f1a7b7b27f8d857db1f560a975c91067189a6e0f5aeda982219d'}, {'id': 'p03', 'revision': 1, 'content': 'p031', 'requires': [], 'revoked': False, 'sha256': '23b0d24b075abfc1369c4f18b00e18a92c0fd86c2240681c6343bd178c114394'}, {'id': 'p03', 'revision': 2, 'content': 'p032', 'requires': [], 'revoked': False, 'sha256': 'ad6dee037712c4c7711759121437fa07112f4810d885fa975b2a296ebddbbd97'}, {'id': 'p03', 'revision': 3, 'content': 'p033', 'requires': [], 'revoked': False, 'sha256': '4fd8764162444000567f93db48ccd43afb8d75b3e00c24fc1c829714bbc9ae4d'}, {'id': 'p04', 'revision': 1, 'content': 'p041', 'requires': [], 'revoked': False, 'sha256': 'a7c038f284a20429b986c9d301be769789a1d5ea59749a73b3df5264d19d5b47'}, {'id': 'p04', 'revision': 2, 'content': 'p042', 'requires': [], 'revoked': False, 'sha256': '9950d25d9a9e87369c24db6e8cbe2d0a7b50732a2e5a685edcfa209f6f11c757'}, {'id': 'p04', 'revision': 3, 'content': 'p043', 'requires': [], 'revoked': False, 'sha256': 'eef564ddc3a3f235d1faf5897a2b5bc97bebebdecf52b6a8a7a0f180962fbd5a'}, {'id': 'p05', 'revision': 1, 'content': 'p051', 'requires': [], 'revoked': False, 'sha256': '89f780cf502a37e86503dd0f5a3836d59100b74d86423ba57a2f35ad4698e710'}, {'id': 'p05', 'revision': 2, 'content': 'p052', 'requires': [], 'revoked': False, 'sha256': '58cb8d75e21ed14f530f38bbb7841f25545fa4e2959b57346810079029e6be4d'}, {'id': 'p05', 'revision': 3, 'content': 'p053', 'requires': [], 'revoked': False, 'sha256': 'd669087b97e577defc996863dea529f7c3fbbbc1a35bbbf5bde45b95443835c9'}, {'id': 'p06', 'revision': 1, 'content': 'p061', 'requires': [], 'revoked': False, 'sha256': 'd8226a0619a4ac0ee8d4c3b4c012747ee01e6226fee8f98bdfee96f511f05ba2'}, {'id': 'p06', 'revision': 2, 'content': 'p062', 'requires': [], 'revoked': False, 'sha256': 'f015438fc90169a86a5faba3976932bed0d76360cd09790d0caa9d4f352bc6d8'}, {'id': 'p06', 'revision': 3, 'content': 'p063', 'requires': [], 'revoked': False, 'sha256': '1fa89db80a03410c117968993762678b22e1732bf31c3a9cb342bac4ed6b68fb'}, {'id': 'p07', 'revision': 1, 'content': 'p071', 'requires': [], 'revoked': False, 'sha256': '2b7282bc75fb0684a92fc25f9438a27bfa12f57561a419d15885ea3ee638712c'}, {'id': 'p07', 'revision': 2, 'content': 'p072', 'requires': [], 'revoked': False, 'sha256': 'ad8e6a3b58f0829f458829bd8c221baf92c82fe0e9252aeb9576b3344f0c55c6'}, {'id': 'p07', 'revision': 3, 'content': 'p073', 'requires': [], 'revoked': False, 'sha256': 'b8503a17571a9d1a7a55fe613ad841a9255e104708801d860221d6b21a073b0f'}, {'id': 'p08', 'revision': 1, 'content': 'p081', 'requires': [], 'revoked': False, 'sha256': '8bc685572dd5fe82b2a2eea623bd824e1a7518325454ef6c6992855377c3e9b7'}, {'id': 'p08', 'revision': 2, 'content': 'p082', 'requires': [], 'revoked': False, 'sha256': '3a7da098643992e1c58572e7aac063b47283f906e8a581cd305c341dca7a8222'}, {'id': 'p08', 'revision': 3, 'content': 'p083', 'requires': [], 'revoked': False, 'sha256': '04190c1aaae36fd7b02bb72be7b036a762e3924004a8a727c22f34d773affbe7'}, {'id': 'p09', 'revision': 1, 'content': 'p091', 'requires': [], 'revoked': False, 'sha256': 'f4ed02dbffff1ebb7d52a6b22873da356334ee1bb8af257f27dfaef45cd2e762'}, {'id': 'p09', 'revision': 2, 'content': 'p092', 'requires': [], 'revoked': False, 'sha256': '9b93b861c3c1759cb6a6e3ee7825da47a685dd2f370174aa8559c1c3a4ced42f'}, {'id': 'p09', 'revision': 3, 'content': 'p093', 'requires': [], 'revoked': False, 'sha256': 'e162edacfec8f3524e3acc309bbe8a6f310a65f8d0c7a7c6d39e4f602e2cc929'}, {'id': 'p10', 'revision': 1, 'content': 'p101', 'requires': [], 'revoked': False, 'sha256': '3e91adc4a3e57e6eb7af1a9b334999553548f3a954c62920aecef6b5d01ed6a4'}, {'id': 'p10', 'revision': 2, 'content': 'p102', 'requires': [], 'revoked': False, 'sha256': 'b89b24920b1620a8d4763e0656d58bd3b8fbc06586ad22d6e60de3523b5f8269'}, {'id': 'p10', 'revision': 3, 'content': 'p103', 'requires': [], 'revoked': False, 'sha256': 'b42de5d330580d87190f8d2ef17954873a5675ff45e05a9549d12f4a5be2773c'}, {'id': 'p11', 'revision': 1, 'content': 'p111', 'requires': [], 'revoked': False, 'sha256': '2023b53307841fc35bce7972ae04065c8c716fb0ea2082a14ca6e52dc3be866e'}, {'id': 'p11', 'revision': 2, 'content': 'p112', 'requires': [], 'revoked': False, 'sha256': 'a06c80c769d1fece3bbc4b11a326f0ea05348e1002b10f3b8fb4447ecdad6a32'}, {'id': 'p11', 'revision': 3, 'content': 'p113', 'requires': [], 'revoked': False, 'sha256': '967ab19f1a8bc8bcdb07d5e7798379e92136c5788f859d7b0622bbefc35ca1af'}], 'commands': [{'op': 'install', 'roots': [['p00', 1, 3], ['p01', 1, 3], ['p02', 1, 3], ['p03', 1, 3], ['p04', 1, 3], ['p05', 1, 3], ['p06', 1, 3], ['p07', 1, 3], ['p08', 1, 3], ['p09', 1, 3], ['p10', 1, 3], ['p11', 1, 3]]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed'], 'installed': [['p00', 3, 'p003'], ['p01', 3, 'p013'], ['p02', 3, 'p023'], ['p03', 3, 'p033'], ['p04', 3, 'p043'], ['p05', 3, 'p053'], ['p06', 3, 'p063'], ['p07', 3, 'p073'], ['p08', 3, 'p083'], ['p09', 3, 'p093'], ['p10', 3, 'p103'], ['p11', 3, 'p113']]}
    assert request == before

