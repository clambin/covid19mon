from abc import ABC
import logging
from datetime import datetime
import pytz
from prometheus_client import Summary, Gauge
from pimetrics.probe import APIProbe
from src.pgconnector import DBError
from src.countries import country_codes
from src.metrics import MetricsPusher

REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request', ['server', 'endpoint'])
GAUGES = {
    'lastReported': Gauge('covid_last_reported_seconds', 'Timestamp of last update (epoch)'),
}


class CovidProbe(APIProbe, ABC):
    def __init__(self, api_key):
        super().__init__('https://covid-19-coronavirus-statistics.p.rapidapi.com')
        self.headers = {
            'x-rapidapi-key': api_key,
            'x-rapidapi-host': 'covid-19-coronavirus-statistics.p.rapidapi.com'
        }

    def apicall(self, endpoint, params=None):
        with REQUEST_TIME.labels(self.url, endpoint).time():
            return self.call(endpoint, headers=self.headers, params=params)


class CovidCountryProbe(CovidProbe):
    def __init__(self, api_key, dbconnector=None, pushgateway_url=None):
        super().__init__(api_key)
        self._countries = None
        self._bad_countries = []
        self._dbconnector = dbconnector
        self._pushgateway = MetricsPusher(pushgateway_url) if pushgateway_url else None

    def apicall(self, endpoint, country=None):
        params = {'country': country} if country else None
        return super().apicall(endpoint, params)

    def report(self, output):
        if self._dbconnector:
            try:
                self._dbconnector.addmany(output)
            except DBError as err:
                logging.error(f'Could not insert data in covid19 db: {err}')
        if self._pushgateway:
            self._pushgateway.report(output)
        logging.info(f'{len(output)} new records')

    def measure(self):
        def nonetozero(val):
            return val if val is not None else 0
        output = {}
        last_updated = self._dbconnector.get_last_updated() if self._dbconnector else None
        stats = self.apicall('/v1/stats')
        if stats:
            for entry in stats['data']['covid19Stats']:
                country = entry['country']
                if country not in country_codes:
                    if country not in self._bad_countries:
                        logging.warning(f'Could not find country code for "{country}". Skipping ...')
                        self._bad_countries.append(country)
                    continue
                update = pytz.UTC.localize(datetime.strptime(entry['lastUpdate'], '%Y-%m-%dT%H:%M:%S+00:00'))
                if last_updated and country in last_updated.keys() and update <= last_updated[country]:
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
                output[country]['time'] = datetime.strptime(entry['lastUpdate'], '%Y-%m-%dT%H:%M:%S+00:00')
        return output


class CovidLastUpdateProbe(CovidProbe):
    def __init__(self, api_key):
        super().__init__(api_key)

    def report(self, output):
        if 'lastReported' in output:
            GAUGES['lastReported'].set(output['lastReported'])

    def measure(self):
        output = {}
        stats = self.apicall('/v1/total')
        if stats:
            utc_time = datetime.strptime(stats['data']['lastReported'], "%Y-%m-%dT%H:%M:%S+00:00")
            output['lastReported'] = (utc_time - datetime(1970, 1, 1)).total_seconds()
        return output
