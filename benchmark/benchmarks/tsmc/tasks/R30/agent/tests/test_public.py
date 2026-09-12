import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'artifacts': [], 'commands': []}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [], 'installed': []}
    assert request == before

def test_one():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed'], 'installed': [['a', 1, 'a']]}
    assert request == before

def test_pinned_old_revision():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}, {'id': 'a', 'revision': 2, 'content': 'new', 'requires': [], 'revoked': False, 'sha256': '11507a0e2f5e69d5dfa40a62a1bd7b6ee57e6bcd85c67c9b8431b36fff21c437'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed'], 'installed': [['a', 1, 'a']]}
    assert request == before

def test_failed_replacement():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a', 'requires': [], 'revoked': False, 'sha256': 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb'}, {'id': 'b', 'revision': 1, 'content': 'b', 'requires': [], 'revoked': False, 'sha256': '3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d'}], 'commands': [{'op': 'install', 'roots': [['a', 1]], 'crash': False}, {'op': 'install', 'roots': [['b', 1]], 'crash': True}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed', 'crashed', 'restarted'], 'installed': [['a', 1, 'a']]}
    assert request == before

def test_range_backtracks_shared_pin():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [['b', 2]], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}, {'id': 'b', 'revision': 1, 'content': 'b1', 'requires': [], 'revoked': False, 'sha256': '7dc96f776c8423e57a2785489a3f9c43fb6e756876d6ad9a9cac4aa4e72ec193'}, {'id': 'b', 'revision': 2, 'content': 'b2', 'requires': [], 'revoked': False, 'sha256': '4814d92093ac8a0f4a2163ab87dee509ba306a58f5888be0edcb2fcd0712028b'}], 'commands': [{'op': 'install', 'roots': [['a', 1, 2], ['b', 1]]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed'], 'installed': [['b', 1, 'b1'], ['a', 1, 'a1']]}
    assert request == before

def test_range_prefers_highest_valid():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [['b', 2]], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}, {'id': 'b', 'revision': 1, 'content': 'b1', 'requires': [], 'revoked': False, 'sha256': '7dc96f776c8423e57a2785489a3f9c43fb6e756876d6ad9a9cac4aa4e72ec193'}, {'id': 'b', 'revision': 2, 'content': 'b2', 'requires': [], 'revoked': False, 'sha256': '4814d92093ac8a0f4a2163ab87dee509ba306a58f5888be0edcb2fcd0712028b'}], 'commands': [{'op': 'install', 'roots': [['a', 1, 2]]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['installed'], 'installed': [['b', 2, 'b2'], ['a', 2, 'a2']]}
    assert request == before

def test_intervening_install_stales_ticket():
    request = {'artifacts': [{'id': 'a', 'revision': 1, 'content': 'a1', 'requires': [['b', 1]], 'revoked': False, 'sha256': 'f55ff16f66f43360266b95db6f8fec01d76031054306ae4a4b380598f6cfd114'}, {'id': 'a', 'revision': 2, 'content': 'a2', 'requires': [['b', 2]], 'revoked': False, 'sha256': '2c3a4249d77070058649dbd822dcaf7957586fce428cfb2ca88b94741eda8b07'}, {'id': 'b', 'revision': 1, 'content': 'b1', 'requires': [], 'revoked': False, 'sha256': '7dc96f776c8423e57a2785489a3f9c43fb6e756876d6ad9a9cac4aa4e72ec193'}, {'id': 'b', 'revision': 2, 'content': 'b2', 'requires': [], 'revoked': False, 'sha256': '4814d92093ac8a0f4a2163ab87dee509ba306a58f5888be0edcb2fcd0712028b'}], 'commands': [{'op': 'prepare', 'roots': [['a', 1]], 'id': 'p'}, {'op': 'install', 'roots': [['b', 2]]}, {'op': 'commit', 'id': 'p'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['prepared', 'installed', 'stale'], 'installed': [['b', 2, 'b2']]}
    assert request == before


def test_public_cli_fixture():
    import json
    from pathlib import Path
    import subprocess
    import sys
    completed = subprocess.run(
        [sys.executable, "-m", "fabops", "--input", "data/request.json"],
        capture_output=True, text=True, timeout=10, check=True)
    assert json.loads(completed.stdout) == json.loads(Path("data/expected.json").read_text())
