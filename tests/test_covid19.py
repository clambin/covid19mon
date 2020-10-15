import json
import os
from src.covid19 import CoronaStats, covid19, CovidDBConnector
from src.configuration import get_configuration
from tests.test_pgconnector import get_dbenv


class CoronaStatsTest(CoronaStats):
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
                return CoronaStatsTest.Response(200, ''.join(output.readlines()))
        else:
            return CoronaStatsTest.Response(500, '')


def test_covidstats():
    covid = CoronaStatsTest()
    covid.run()
    measured = covid.measured()
    assert measured['Belgium'] == {'code': 'BE', 'confirmed': 85911, 'deaths': 9898, 'recovered': 18490}
    assert measured['US'] == {'code': 'US', 'confirmed': 6113510, 'deaths': 185720, 'recovered': 2231757}
    assert '???' not in measured


def test_bad_covidstats():
    covid = CoronaStatsTest(False)
    covid.run()
    measured = covid.measured()
    assert not measured


def test_main():
    host, port, database, user, password = get_dbenv()
    connector = CovidDBConnector(host, port, database, user, password)
    connector._drop_covid_db()
    config = get_configuration(f'--once --debug '
                               f'--apikey {os.getenv("API_KEY")} '
                               f'--postgres-host {host} '
                               f'--postgres-port {port} '
                               f'--postgres-database {database} '
                               f'--postgres-user {user} '
                               f'--postgres-password {password}'.split())
    assert config
    covid19(config)
    rows = connector.list()
    assert rows
    assert len(rows) > 0
    for row in rows:
        assert isinstance(row, tuple)
        assert len(row) == 6
