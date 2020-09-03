import json
from src.covid19 import CoronaStats


class CoronaStatsTest(CoronaStats):
    class Response:
        def __init__(self, status_code, output):
            self.status_code = status_code
            self.reason = ''
            self.data = json.loads(output)

        def json(self):
            return self.data

    def __init__(self):
        super().__init__(None, None)

    def get(self, endpoint=None, headers=None, body=None, params=None):
        with open('data/covid19.json', 'r') as output:
            return CoronaStatsTest.Response(200, ''.join(output.readlines()))


def test_covid19():
    covid = CoronaStatsTest()
    covid.run()
    measured = covid.measured()
    assert measured['Belgium'] == {'code': 'BE', 'confirmed': 85911, 'deaths': 9898, 'recovered': 18490}
    assert measured['US'] == {'code': 'US', 'confirmed': 6113510, 'deaths': 185720, 'recovered': 2231757}
    assert '???' not in measured
