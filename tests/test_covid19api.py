from datetime import datetime
from src.covid19api import Covid19API


class CovidPGConnectorStub:
    def __init__(self, data):
        self.data = data

    def list(self, end_time=None):
        return self.data


test_data = [
    (datetime(2020, 1, 1), 'US', '', 1, 0, 0),
    (datetime(2020, 1, 5), 'BE', '', 2, 0, 0),
    (datetime(2020, 1, 7), 'US', '', 2, 0, 0),
    (datetime(2020, 1, 9), 'BE', '', 9, 0, 0),
    (datetime(2020, 1, 9), 'ML', '', 9, 0, 1)
]


def test_covid19api():
    covid19api = Covid19API()
    covid19api.set_covidpg(CovidPGConnectorStub(test_data))
    assert covid19api.get_data([('confirmed', '')]) == [
        {
            'target': 'confirmed',
            'datapoints': [
                [1, 1577836800000],
                [3, 1578182400000],
                [4, 1578355200000],
                [20, 1578528000000],
            ]
        }
    ]
    assert covid19api.get_data([('confirmed-delta', '')]) == [
        {
            'target': 'confirmed-delta',
            'datapoints': [
                [1, 1577836800000],
                [2, 1578182400000],
                [1, 1578355200000],
                [16, 1578528000000],
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
    assert covid19api.get_data([('death-delta', '')]) == [
        {
            'target': 'death-delta',
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
    assert covid19api.get_data([('recovered-delta', '')]) == [
        {
            'target': 'recovered-delta',
            'datapoints': [
                [0, 1577836800000],
                [0, 1578182400000],
                [0, 1578355200000],
                [1, 1578528000000],
            ]
        }
    ]
    assert covid19api.get_data([('active', '')]) == [
        {
            'target': 'active',
            'datapoints': [
                [1, 1577836800000],
                [3, 1578182400000],
                [4, 1578355200000],
                [19, 1578528000000],
            ]
        }
    ]
    assert covid19api.get_data([('active-delta', '')]) == [
        {
            'target': 'active-delta',
            'datapoints': [
                [1, 1577836800000],
                [2, 1578182400000],
                [1, 1578355200000],
                [15, 1578528000000],
            ]
        }
    ]
