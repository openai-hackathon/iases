import copy
import pytest
from fabops.domain import run


def test_reordered_manifest_resume():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}, {'index': 1, 'rows': 1, 'sha256': 'be965608df71e597007ce9aca1c90d92f7347a693267c4fb440397a33b0d676e'}]}, {'op': 'begin', 'id': 'b', 'manifest': [{'index': 1, 'rows': 1, 'sha256': 'be965608df71e597007ce9aca1c90d92f7347a693267c4fb440397a33b0d676e'}, {'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}, {'op': 'chunk', 'id': 'b', 'index': 1, 'rows': [{'key': 'b', 'value': 2}]}, {'op': 'restart'}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'finish', 'id': 'b', 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'resumed', 'staged', 'restarted', 'staged', 'committed'], 'published': {'b': [{'key': 'a', 'value': 1}, {'key': 'b', 'value': 2}]}, 'staged': [['b', 0], ['b', 1]], 'states': {'b': 'committed'}}
    assert request == before

def test_initial_manifest_unsorted():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 1, 'rows': 1, 'sha256': 'be965608df71e597007ce9aca1c90d92f7347a693267c4fb440397a33b0d676e'}, {'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'chunk', 'id': 'b', 'index': 1, 'rows': [{'key': 'b', 'value': 2}]}, {'op': 'finish', 'id': 'b', 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'staged', 'committed'], 'published': {'b': [{'key': 'a', 'value': 1}, {'key': 'b', 'value': 2}]}, 'staged': [['b', 0], ['b', 1]], 'states': {'b': 'committed'}}
    assert request == before

def test_incomplete_batch_is_invisible():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}, {'index': 1, 'rows': 1, 'sha256': 'be965608df71e597007ce9aca1c90d92f7347a693267c4fb440397a33b0d676e'}]}, {'op': 'chunk', 'id': 'b', 'index': 1, 'rows': [{'key': 'b', 'value': 2}]}, {'op': 'finish', 'id': 'b', 'crash': False}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'incomplete', 'restarted'], 'published': {}, 'staged': [['b', 1]], 'states': {'b': 'open'}}
    assert request == before

def test_duplicate_cross_chunk_key():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}, {'index': 1, 'rows': 1, 'sha256': '28fd0a417392d40fdee7978d8f90ef5f7b7efa07d75017a2599b343c4db26301'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'chunk', 'id': 'b', 'index': 1, 'rows': [{'key': 'a', 'value': 9}]}, {'op': 'finish', 'id': 'b', 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'staged', 'invalid'], 'published': {}, 'staged': [['b', 0], ['b', 1]], 'states': {'b': 'open'}}
    assert request == before

def test_duplicate_within_chunk():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 2, 'sha256': 'b91faea1aa58e2576cb7542cc3b5fdf93b3c7ec47d241d7313be9f9adb586c2c'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 1}, {'key': 'a', 'value': 1}]}, {'op': 'finish', 'id': 'b', 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'invalid'], 'published': {}, 'staged': [['b', 0]], 'states': {'b': 'open'}}
    assert request == before

def test_retry_after_crash():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}, {'index': 1, 'rows': 1, 'sha256': 'be965608df71e597007ce9aca1c90d92f7347a693267c4fb440397a33b0d676e'}]}, {'op': 'chunk', 'id': 'b', 'index': 1, 'rows': [{'key': 'b', 'value': 2}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'finish', 'id': 'b', 'crash': True}, {'op': 'restart'}, {'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}, {'index': 1, 'rows': 1, 'sha256': 'be965608df71e597007ce9aca1c90d92f7347a693267c4fb440397a33b0d676e'}]}, {'op': 'finish', 'id': 'b', 'crash': False}, {'op': 'finish', 'id': 'b', 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'staged', 'crashed', 'restarted', 'resumed', 'committed', 'committed'], 'published': {'b': [{'key': 'a', 'value': 1}, {'key': 'b', 'value': 2}]}, 'staged': [['b', 0], ['b', 1]], 'states': {'b': 'committed'}}
    assert request == before

def test_immutable_manifest():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}, {'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'be965608df71e597007ce9aca1c90d92f7347a693267c4fb440397a33b0d676e'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'finish', 'id': 'b', 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'conflict', 'staged', 'committed'], 'published': {'b': [{'key': 'a', 'value': 1}]}, 'staged': [['b', 0]], 'states': {'b': 'committed'}}
    assert request == before

def test_duplicate_chunk():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'restart'}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'finish', 'id': 'b', 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'restarted', 'duplicate', 'committed'], 'published': {'b': [{'key': 'a', 'value': 1}]}, 'staged': [['b', 0]], 'states': {'b': 'committed'}}
    assert request == before

def test_closed_upload():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'finish', 'id': 'b', 'crash': False}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 9}]}, {'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'committed', 'closed', 'committed'], 'published': {'b': [{'key': 'a', 'value': 1}]}, 'staged': [['b', 0]], 'states': {'b': 'committed'}}
    assert request == before

def test_empty_manifest():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': []}, {'op': 'finish', 'id': 'b', 'crash': False}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'committed', 'restarted'], 'published': {'b': []}, 'staged': [], 'states': {'b': 'committed'}}
    assert request == before

def test_empty_chunk():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 0, 'sha256': '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': []}, {'op': 'finish', 'id': 'b', 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'committed'], 'published': {'b': []}, 'staged': [['b', 0]], 'states': {'b': 'committed'}}
    assert request == before

def test_invalid_index():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}, {'op': 'chunk', 'id': 'b', 'index': 1, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'finish', 'id': 'b', 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'invalid', 'incomplete'], 'published': {}, 'staged': [], 'states': {'b': 'open'}}
    assert request == before

def test_unknown_upload():
    request = {'commands': [{'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'finish', 'id': 'b', 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['missing', 'missing'], 'published': {}, 'staged': [], 'states': {}}
    assert request == before

def test_batch_isolation():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}, {'op': 'begin', 'id': 'other', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}, {'op': 'chunk', 'id': 'other', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'finish', 'id': 'b', 'crash': False}, {'op': 'finish', 'id': 'other', 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'started', 'staged', 'incomplete', 'committed'], 'published': {'other': [{'key': 'a', 'value': 1}]}, 'staged': [['other', 0]], 'states': {'b': 'open', 'other': 'committed'}}
    assert request == before

def test_crash_preserves_other_batch_visibility():
    request = {'commands': [{'op': 'begin', 'id': 'other', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}, {'op': 'chunk', 'id': 'other', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'finish', 'id': 'other', 'crash': False}, {'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}, {'index': 1, 'rows': 1, 'sha256': 'be965608df71e597007ce9aca1c90d92f7347a693267c4fb440397a33b0d676e'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'chunk', 'id': 'b', 'index': 1, 'rows': [{'key': 'b', 'value': 2}]}, {'op': 'finish', 'id': 'b', 'crash': True}, {'op': 'restart'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'committed', 'started', 'staged', 'staged', 'crashed', 'restarted'], 'published': {'other': [{'key': 'a', 'value': 1}]}, 'staged': [['b', 0], ['b', 1], ['other', 0]], 'states': {'b': 'open', 'other': 'committed'}}
    assert request == before

def test_duplicate_manifest_index():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}, {'index': 0, 'rows': 1, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['invalid'], 'published': {}, 'staged': [], 'states': {}}
    assert request == before

def test_count_failure_with_matching_digest():
    request = {'commands': [{'op': 'begin', 'id': 'b', 'manifest': [{'index': 0, 'rows': 2, 'sha256': '43691b8f386ca92b624ed70f01a36de7d6d9bf36b747ac3b7dd28bb5613a5eb8'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'a', 'value': 1}]}, {'op': 'finish', 'id': 'b', 'crash': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'invalid', 'incomplete'], 'published': {}, 'staged': [], 'states': {'b': 'open'}}
    assert request == before

