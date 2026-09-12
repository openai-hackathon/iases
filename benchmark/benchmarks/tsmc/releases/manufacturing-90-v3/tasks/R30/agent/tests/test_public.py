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


def test_public_cli_fixture():
    import json
    from pathlib import Path
    import subprocess
    import sys
    completed = subprocess.run(
        [sys.executable, "-m", "fabops", "--input", "data/request.json"],
        capture_output=True, text=True, timeout=10, check=True)
    assert json.loads(completed.stdout) == json.loads(Path("data/expected.json").read_text())
