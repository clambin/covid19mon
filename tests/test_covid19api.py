from datetime import datetime
from src.covid19api import Covid19API


class CovidPGConnectorStub:
    def __init__(self, data):
        self.data = data

    def list(self):
        return self.data


test_data = [
    (datetime(2020, 1, 1), 'US', '', 1, 0, 0),
    (datetime(2020, 1, 5), 'BE', '', 2, 0, 0),
    (datetime(2020, 1, 7), 'US', '', 2, 0, 0),
    (datetime(2020, 1, 9), 'BE', '', 9, 0, 0),
    (datetime(2020, 1, 9), 'ML', '', 9, 0, 1)
]


def test_covid19api():
    pgcovid = CovidPGConnectorStub(test_data)
    covid19api = Covid19API(pgcovid)
    assert covid19api.get_data([('confirmed', '')]) == [
        {
            'target': 'recovered',
            'datapoints': [
                [1, 1577836800000],
                [3, 1578182400000],
                [4, 1578355200000],
                [20, 1578528000000],
            ]
        }
    ]
    assert covid19api.get_data([('death', '')]) == [
        {
            'target': 'death',
            'datapoints': [
                [0, 1577836800000],
                [0, 1578182400000],
                [0, 1578355200000],
                [0, 1578528000000],
            ]
        }
    ]
    assert covid19api.get_data([('recovered', '')]) == [
        {
            'target': 'recovered',
            'datapoints': [
                [0, 1577836800000],
                [0, 1578182400000],
                [0, 1578355200000],
                [1, 1578528000000],
            ]
        }
    ]
