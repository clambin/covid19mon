import json
import os
from src.covid19 import covid19
from src.covidprobe import CovidProbe
from src.covidpgconnector import CovidPGConnector
from src.configuration import get_configuration
from tests.test_pgconnector import get_dbenv


class CovidTestProbe(CovidProbe):
    class Response:
        def __init__(self, status_code, output):
            self.status_code = status_code
            self.reason = ''
            self.data = json.loads(output) if output else None

        def json(self):
            return self.data

    def __init__(self, success=True):
        super().__init__(None, None)
        self.success = success

    def get(self, endpoint=None, headers=None, body=None, params=None):
        if self.success:
            with open('data/covid19.json', 'r') as output:
                return CovidTestProbe.Response(200, ''.join(output.readlines()))
        else:
            return CovidTestProbe.Response(500, '')


def test_covidstats():
    covid = CovidTestProbe()
    covid.run()
    measured = covid.measured()
    assert measured['Belgium'] == {'code': 'BE', 'confirmed': 85911, 'deaths': 9898, 'recovered': 18490}
    assert measured['US'] == {'code': 'US', 'confirmed': 6113510, 'deaths': 185720, 'recovered': 2231757}
    assert '???' not in measured


def test_bad_covidstats():
    covid = CovidTestProbe(False)
    covid.run()
    measured = covid.measured()
    assert not measured

