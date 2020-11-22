from covid19.metrics import MetricsPusher


def test_metrics():
    pusher = MetricsPusher(None)
    pusher.report({'Belgium': {}})
    assert pusher.reported() == {'Belgium': 1}
    pusher.report({'US': {}})
    assert pusher.reported() == {'US': 1}
    pusher.report({'Belgium': {}, 'US': {}})
    assert pusher.reported() == {'Belgium': 1, 'US': 1}
