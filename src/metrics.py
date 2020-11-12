from prometheus_client import Gauge, CollectorRegistry, push_to_gateway


class MetricsPusher:
    def __init__(self, pushgateway, job='covid19mon'):
        self._pushgateway = pushgateway
        self._job = job
        self._registry = CollectorRegistry()
        self._gauges = {
            'reported': Gauge('covid_reported_count', 'New entries for country', ['country'], registry=self._registry)
        }
        self._reported = None

    def report(self, metrics):
        self._reported = dict()
        for country, value in metrics.items():
            self._reported[country] = 1
            self._gauges['reported'].labels(country).set(self._reported[country])
        if self._pushgateway:
            push_to_gateway(self._pushgateway, job=self._job, registry=self._registry)

    def reported(self):
        return self._reported
