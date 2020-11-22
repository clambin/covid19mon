import datetime
from pimetrics.stubs import APIStub
from covid19.probes.covid import CovidCountryProbe, CovidLastUpdateProbe

testfiles = {
    '/v1/stats': {
        'filename': 'data/covid_countries.json',
    },
    '/v1/total': {
        'filename': 'data/covid_last_update.json',
    }
}


class CovidCountryTestProbe(APIStub, CovidCountryProbe):
    def __init__(self):
        APIStub.__init__(self, testfiles)
        CovidCountryProbe.__init__(self, None)


class CovidLastUpdateTestProbe(APIStub, CovidLastUpdateProbe):
    def __init__(self):
        APIStub.__init__(self, testfiles)
        CovidLastUpdateProbe.__init__(self, None)


def test_covidstats():
    covid = CovidCountryTestProbe()
    covid.run()
    measured = covid.measured()
    assert measured['Belgium'] == {
        'code': 'BE', 'confirmed': 85911, 'deaths': 9898, 'recovered': 18490,
        'time': datetime.datetime(2020, 9, 3, 4, 28, 22)
    }
    assert measured['US'] == {
        'code': 'US', 'confirmed': 6113510, 'deaths': 185720, 'recovered': 2231757,
        'time': datetime.datetime(2020, 9, 3, 4, 28, 22)
    }
    assert '???' not in measured


# def test_bad_covidstats():
#   covid = CovidCountryTestProbe()
#   covid.success = False
#   covid.run()
#   measured = covid.measured()
#   assert not measured


def test_covidlastupdate():
    covid = CovidLastUpdateTestProbe()
    covid.run()
    measured = covid.measured()
    assert measured['lastReported'] == 1603772685
