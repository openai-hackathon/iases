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

def test_atomic_shared_scope_group():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'a', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'begin', 'id': 'b', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': '75aef52e24d7b1135d74ec783c970bbd9ddb05b3b2bbc29f097c2fd653c24ccf'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'q', 'value': 2}]}, {'op': 'finish_group', 'ids': ['b', 'a']}, {'op': 'read', 'scope': 'fab'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'started', 'staged', 'committed', {'values': {'k': [1, 1], 'q': [1, 2]}, 'versions': {'k': 1, 'q': 1}}], 'published': {'a': [{'key': 'k', 'value': 1}], 'b': [{'key': 'q', 'value': 2}]}, 'staged': [['a', 0], ['b', 0]], 'states': {'a': 'committed', 'b': 'committed'}}
    assert request == before

def test_group_conflicting_key():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'a', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'begin', 'id': 'b', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'finish_group', 'ids': ['a', 'b']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'started', 'staged', 'invalid'], 'published': {}, 'staged': [['a', 0], ['b', 0]], 'states': {'a': 'open', 'b': 'open'}}
    assert request == before

def test_group_crash_recovery():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'a', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'begin', 'id': 'b', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': '75aef52e24d7b1135d74ec783c970bbd9ddb05b3b2bbc29f097c2fd653c24ccf'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'q', 'value': 2}]}, {'op': 'finish_group', 'ids': ['a', 'b'], 'crash': True}, {'op': 'restart'}, {'op': 'read', 'scope': 'fab'}, {'op': 'finish_group', 'ids': ['a', 'b']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'started', 'staged', 'crashed', 'restarted', {'values': {}, 'versions': {}}, 'committed'], 'published': {'a': [{'key': 'k', 'value': 1}], 'b': [{'key': 'q', 'value': 2}]}, 'staged': [['a', 0], ['b', 0]], 'states': {'a': 'committed', 'b': 'committed'}}
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
