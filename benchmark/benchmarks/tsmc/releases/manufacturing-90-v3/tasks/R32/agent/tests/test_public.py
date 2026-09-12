import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'commands': []}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [], 'published': {}, 'staged': [], 'states': {}}
    assert request == before

def test_complete_one():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'finish', 'id': 'b', 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'committed'], 'published': {'b': [{'key': 'a', 'value': 1}]}, 'staged': [['b', 0]], 'states': {'b': 'committed'}}
    assert request == before

def test_digest_failure_is_not_staged():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 9}]}, {'op': 'finish', 'id': 'b', 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'invalid', 'incomplete'], 'published': {}, 'staged': [], 'states': {'b': 'open'}}
    assert request == before

def test_crash_before_publication_commit():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'finish', 'id': 'b', 'crash': True}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'crashed', 'restarted'], 'published': {}, 'staged': [['b', 0]], 'states': {'b': 'open'}}
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
