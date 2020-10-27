import json
from abc import ABC
from pimetrics.probe import APIProbe
from src.covidprobe import CovidCountryProbe, CovidLastUpdateProbe


class _ResponseStub:
    def __init__(self, status_code, output):
        self.status_code = status_code
        self.reason = ''
        self.data = json.loads(output) if output else None

    def json(self):
        return self.data


class APIStub(APIProbe, ABC):
    def __init__(self, filename, success=True):
        super().__init__(None)
        self.filename = filename
        self.success = success

    def get(self, endpoint=None, headers=None, body=None, params=None):
        if self.success:
            with open(self.filename, 'r') as output:
                return _ResponseStub(200, ''.join(output.readlines()))
        else:
            return _ResponseStub(500, '')


class CovidCountryTestProbe(APIStub, CovidCountryProbe):
    def __init__(self):
        APIStub.__init__(self, 'data/covid_countries.json')
        CovidCountryProbe.__init__(self, None)


class CovidLastUpdateTestProbe(APIStub, CovidLastUpdateProbe):
    def __init__(self):
        APIStub.__init__(self, 'data/covid_last_update.json')
        CovidLastUpdateProbe.__init__(self, None)


def test_covidstats():
    covid = CovidCountryTestProbe()
    covid.run()
    measured = covid.measured()
    assert measured['Belgium'] == {'code': 'BE', 'confirmed': 85911, 'deaths': 9898, 'recovered': 18490}
    assert measured['US'] == {'code': 'US', 'confirmed': 6113510, 'deaths': 185720, 'recovered': 2231757}
    assert '???' not in measured


def test_bad_covidstats():
    covid = CovidCountryTestProbe()
    covid.success = False
    covid.run()
    measured = covid.measured()
    assert not measured


def test_covidlastupdate():
    covid = CovidLastUpdateTestProbe()
    covid.run()
    measured = covid.measured()
    assert measured['lastReported'] == 1603772685
    covid.success = False
    covid.run()
    assert 'lastReported' not in covid.measured()
