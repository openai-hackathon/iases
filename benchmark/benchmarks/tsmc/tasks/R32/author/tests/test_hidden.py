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

def test_corrupt_chunk_does_not_survive_restart_into_group():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'a', 'index': 0, 'rows': [{'key': 'q', 'value': 2}]}, {'op': 'restart'}, {'op': 'begin', 'id': 'b', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': '75aef52e24d7b1135d74ec783c970bbd9ddb05b3b2bbc29f097c2fd653c24ccf'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'q', 'value': 2}]}, {'op': 'finish_group', 'ids': ['a', 'b']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'invalid', 'restarted', 'started', 'staged', 'incomplete'], 'published': {}, 'staged': [['b', 0]], 'states': {'a': 'open', 'b': 'open'}}
    assert request == before

def test_read_set_stales_disjoint_write():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'a', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'begin', 'id': 'b', 'scope': 'fab', 'read_set': {'k': 0}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': '75aef52e24d7b1135d74ec783c970bbd9ddb05b3b2bbc29f097c2fd653c24ccf'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'q', 'value': 2}]}, {'op': 'finish', 'id': 'a'}, {'op': 'finish', 'id': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'started', 'staged', 'committed', 'stale'], 'published': {'a': [{'key': 'k', 'value': 1}]}, 'staged': [['a', 0], ['b', 0]], 'states': {'a': 'committed', 'b': 'open'}}
    assert request == before

def test_update_preserves_old_audit():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'a', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'finish', 'id': 'a'}, {'op': 'begin', 'id': 'b', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'b8d9ba3b3e6a25227bb4954d6fda6efd43c820a125d270be9b710973544bcbe7'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'k', 'expected': 1, 'revision': 2, 'value': 9}]}, {'op': 'finish', 'id': 'b'}, {'op': 'restart'}, {'op': 'read', 'scope': 'fab'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'committed', 'started', 'staged', 'committed', 'restarted', {'values': {'k': [2, 9]}, 'versions': {'k': 2}}], 'published': {'a': [{'key': 'k', 'value': 1}], 'b': [{'key': 'k', 'expected': 1, 'revision': 2, 'value': 9}]}, 'staged': [['a', 0], ['b', 0]], 'states': {'a': 'committed', 'b': 'committed'}}
    assert request == before

def test_tombstone_prevents_resurrection():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'a', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'finish', 'id': 'a'}, {'op': 'begin', 'id': 'b', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': '325519d6af81d74b3e4fc2fd6a93ac3e2c46ed9761adf485baa419538b7a1626'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'k', 'expected': 1, 'revision': 2, 'deleted': True}]}, {'op': 'finish', 'id': 'b'}, {'op': 'restart'}, {'op': 'begin', 'id': 'c', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'c', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'finish', 'id': 'c'}, {'op': 'read', 'scope': 'fab'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'committed', 'started', 'staged', 'committed', 'restarted', 'started', 'staged', 'stale', {'values': {}, 'versions': {'k': 2}}], 'published': {'a': [{'key': 'k', 'value': 1}], 'b': [{'key': 'k', 'expected': 1, 'revision': 2, 'deleted': True}]}, 'staged': [['a', 0], ['b', 0], ['c', 0]], 'states': {'a': 'committed', 'b': 'committed', 'c': 'open'}}
    assert request == before

def test_group_replay_is_idempotent():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'a', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'begin', 'id': 'b', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': '75aef52e24d7b1135d74ec783c970bbd9ddb05b3b2bbc29f097c2fd653c24ccf'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'q', 'value': 2}]}, {'op': 'finish_group', 'ids': ['a', 'b']}, {'op': 'restart'}, {'op': 'finish_group', 'ids': ['b', 'a', 'a']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'started', 'staged', 'committed', 'restarted', 'committed'], 'published': {'a': [{'key': 'k', 'value': 1}], 'b': [{'key': 'q', 'value': 2}]}, 'staged': [['a', 0], ['b', 0]], 'states': {'a': 'committed', 'b': 'committed'}}
    assert request == before

def test_mixed_closed_group_conflicts():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'a', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'finish', 'id': 'a'}, {'op': 'begin', 'id': 'b', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': '75aef52e24d7b1135d74ec783c970bbd9ddb05b3b2bbc29f097c2fd653c24ccf'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'q', 'value': 2}]}, {'op': 'finish_group', 'ids': ['a', 'b']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'committed', 'started', 'staged', 'conflict'], 'published': {'a': [{'key': 'k', 'value': 1}]}, 'staged': [['a', 0], ['b', 0]], 'states': {'a': 'committed', 'b': 'open'}}
    assert request == before

def test_scope_binding_conflict():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'begin', 'id': 'a', 'scope': 'other', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'conflict'], 'published': {}, 'staged': [], 'states': {'a': 'open'}}
    assert request == before

def test_read_set_binding_conflict():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {'q': 1}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'conflict'], 'published': {}, 'staged': [], 'states': {'a': 'open'}}
    assert request == before

def test_disjoint_namespaces_allow_same_key():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'one', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'a', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'begin', 'id': 'b', 'scope': 'two', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'finish_group', 'ids': ['a', 'b']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'started', 'staged', 'committed'], 'published': {'a': [{'key': 'k', 'value': 1}], 'b': [{'key': 'k', 'value': 1}]}, 'staged': [['a', 0], ['b', 0]], 'states': {'a': 'committed', 'b': 'committed'}}
    assert request == before

def test_all_readsets_use_prestate():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'a', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'begin', 'id': 'b', 'scope': 'fab', 'read_set': {'k': 0}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': '75aef52e24d7b1135d74ec783c970bbd9ddb05b3b2bbc29f097c2fd653c24ccf'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'q', 'value': 2}]}, {'op': 'finish_group', 'ids': ['a', 'b']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'started', 'staged', 'committed'], 'published': {'a': [{'key': 'k', 'value': 1}], 'b': [{'key': 'q', 'value': 2}]}, 'staged': [['a', 0], ['b', 0]], 'states': {'a': 'committed', 'b': 'committed'}}
    assert request == before

def test_staged_write_is_not_supply():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'a', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'begin', 'id': 'b', 'scope': 'fab', 'read_set': {'k': 1}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': '75aef52e24d7b1135d74ec783c970bbd9ddb05b3b2bbc29f097c2fd653c24ccf'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'q', 'value': 2}]}, {'op': 'finish_group', 'ids': ['a', 'b']}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'started', 'staged', 'stale'], 'published': {}, 'staged': [['a', 0], ['b', 0]], 'states': {'a': 'open', 'b': 'open'}}
    assert request == before

def test_stale_row_expected():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'a', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'finish', 'id': 'a'}, {'op': 'begin', 'id': 'b', 'scope': 'fab', 'read_set': {}, 'manifest': [{'index': 0, 'rows': 1, 'sha256': 'eed20258ffbb7c89759fccb7ab17e67f2778bbfd49532f9b550746c83749aae5'}]}, {'op': 'chunk', 'id': 'b', 'index': 0, 'rows': [{'key': 'k', 'value': 1}]}, {'op': 'finish', 'id': 'b'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'committed', 'started', 'staged', 'stale'], 'published': {'a': [{'key': 'k', 'value': 1}]}, 'staged': [['a', 0], ['b', 0]], 'states': {'a': 'committed', 'b': 'open'}}
    assert request == before

def test_empty_upload_readset_checked():
    request = {'commands': [{'op': 'begin', 'id': 'a', 'scope': 'fab', 'read_set': {'k': 1}, 'manifest': [{'index': 0, 'rows': 0, 'sha256': '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945'}]}, {'op': 'chunk', 'id': 'a', 'index': 0, 'rows': []}, {'op': 'finish', 'id': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': ['started', 'staged', 'stale'], 'published': {}, 'staged': [['a', 0]], 'states': {'a': 'open'}}
    assert request == before

