from covid19.apiserver.covid19api import DataCache


def test_add():
    cache = DataCache()
    assert cache.len() == 0
    cache.add('A', {'X': 1, 'Y': 2})
    cache.add('B', 'this is a string')
    assert cache.get('A') == {'X': 1, 'Y': 2}
    assert cache.get('B') == 'this is a string'
    assert cache.len() == 2


def test_get_cache():
    cache = DataCache()
    cache.add('B', 'this is a string')
    assert cache.get('A') is None
    assert cache.get('B') == 'this is a string'


def test_clear():
    cache = DataCache()
    cache.add('B', 'this is a string')
    assert cache.get('B') == 'this is a string'
    cache.clear()
    assert cache.get('B') is None
    assert cache.len() == 0
