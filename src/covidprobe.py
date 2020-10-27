from abc import ABC
import logging
import requests
from datetime import datetime
from prometheus_client import Summary, Gauge
from pimetrics.probe import APIProbe
from src.pgconnector import DBError
from src.countries import country_codes

REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request', ['server', 'endpoint'])
GAUGES = {
    'lastReported': Gauge('covid_last_reported_seconds', 'Timestamp of last update (epoch)'),
}


class CovidProbe(APIProbe, ABC):
    def __init__(self, api_key):
        super().__init__('https://covid-19-coronavirus-statistics.p.rapidapi.com/')
        self.api_key = api_key

    def call(self, endpoint, params=None):
        with REQUEST_TIME.labels(self.url, endpoint).time():
            result = None
            try:
                headers = {
                    'x-rapidapi-key': self.api_key,
                    'x-rapidapi-host': 'covid-19-coronavirus-statistics.p.rapidapi.com'
                }
                response = self.get(endpoint, headers, params=params)
                if response.status_code == 200:
                    result = response.json()
                else:
                    logging.error("%d - %s" % (response.status_code, response.reason))
            except requests.exceptions.RequestException as err:
                logging.warning(f'Failed to call "{self.url}": "{err}')
            return result


class CovidCountryProbe(CovidProbe):
    def __init__(self, api_key, dbconnector=None):
        super().__init__(api_key)
        self.countries = None
        self.dbconnector = dbconnector
        self.bad_countries = []

    def call(self, endpoint, country=None):
        params = {'country': country} if country else None
        return super().call(endpoint, params)

    def report(self, output):
        if self.dbconnector:
            try:
                self.dbconnector.addmany(output)
            except DBError as err:
                logging.error(f'Could not insert data in covid19 db: {err}')

    def measure(self):
        def nonetozero(val):
            return val if val is not None else 0
        output = {}
        stats = self.call('v1/stats')
        if stats:
            for entry in stats['data']['covid19Stats']:
                country = entry['country']
                if country not in country_codes:
                    if country not in self.bad_countries:
                        logging.warning(f'Could not find country code for "{country}". Skipping ...')
                        self.bad_countries.append(country)
                    continue
                if country not in output:
                    output[country] = {
                        # Grafana world map uses country codes ('BE') rather than names ('Belgium')
                        'code': country_codes[country],
                        'confirmed': 0,
                        'deaths': 0,
                        'recovered': 0
                    }
                output[country]['confirmed'] += nonetozero(entry['confirmed'])
                output[country]['deaths'] += nonetozero(entry['deaths'])
                output[country]['recovered'] += nonetozero(entry['recovered'])
        return output


class CovidLastUpdateProbe(CovidProbe):
    def __init__(self, api_key):
        super().__init__(api_key)

    def report(self, output):
        if 'lastReported' in output:
            GAUGES['lastReported'].set(output['lastReported'])

    def measure(self):
        output = {}
        stats = self.call('v1/total')
        if stats:
            utc_time = datetime.strptime(stats['data']['lastReported'], "%Y-%m-%dT%H:%M:%S+00:00")
            output['lastReported'] = (utc_time - datetime(1970, 1, 1)).total_seconds()
        return output
