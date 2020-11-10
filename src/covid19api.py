import os
import cProfile
import json
import logging
import re
from datetime import datetime, date
import waitress
from src.covidpgconnector import CovidPGConnector
from src.version import version
from src.configuration import print_configuration

from flask import Flask, request


class Covid19API:
    def __init__(self):
        self._targets = [
            'confirmed', 'confirmed-delta',
            'death', 'death-delta',
            'recovered', 'recovered-delta',
            'active', 'active-delta'
        ]
        self.covid19pg = None

    @property
    def targets(self):
        return self._targets

    def set_covidpg(self, covidpg):
        self.covid19pg = covidpg

    @staticmethod
    def datetime_to_epoch(ts):
        return int((datetime(ts.year, ts.month, ts.day) - datetime(1970, 1, 1)).total_seconds() * 1000)

    @staticmethod
    def grafana_date_to_epoch(ts):
        # 2019-10-17T21:21:33.596Z
        if ts:
            m = re.match(r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.(\d{3})Z', ts)
            if m:
                return Covid19API.datetime_to_epoch(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        return 0

    @staticmethod
    def is_target(my_target, target_names):
        for t in target_names:
            if t[0] == my_target:
                return True
        return False

    def get_data_by_time_country(self, end_time=None):
        countries = set()
        values = dict()
        for entry in self.covid19pg.list(end_time=end_time):
            time = Covid19API.datetime_to_epoch(entry[0])
            code = entry[1]
            confirmed = entry[3]
            death = entry[4]
            recovered = entry[5]
            if time not in values:
                values[time] = dict()
            if code not in values[time]:
                values[time][code] = {}
            values[time][code] = {'confirmed': confirmed, 'death': death, 'recovered': recovered}
            countries.add(code)
        return values, countries

    def get_data_by_time(self, values, countries, start_time):
        metrics = dict()
        current = dict()
        for t in self.targets:
            metrics[t] = {'target': t, 'datapoints': []}
            current[t] = 0
        last = {
            'confirmed': {country: 0 for country in countries},
            'death': {country: 0 for country in countries},
            'recovered': {country: 0 for country in countries}
        }
        skip_time = Covid19API.grafana_date_to_epoch(start_time)
        for time, time_data in values.items():
            for country, data in time_data.items():
                last['confirmed'][country] = data['confirmed']
                last['death'][country] = data['death']
                last['recovered'][country] = data['recovered']
            previous = current
            current = dict()
            current['confirmed'] = sum(last['confirmed'].values())
            current['death'] = sum(last['death'].values())
            current['recovered'] = sum(last['recovered'].values())
            current['active'] = current['confirmed'] - current['death'] - current['recovered']
            if time < skip_time:
                continue
            for t in self.targets:
                if t.endswith('-delta'):
                    pass
                else:
                    metrics[t]['datapoints'].append([current[t], time])
                    metrics[f'{t}-delta']['datapoints'].append([current[t] - previous[t], time])
        return metrics

    def get_data(self, targets, start_time=None, end_time=None):
        # TODO: support table output: https://grafana.com/grafana/plugins/simpod-json-datasource#query
        logging.debug(f'{start_time} {end_time}')
        values, countries = self.get_data_by_time_country(end_time)
        metrics = self.get_data_by_time(values, countries, start_time)
        output = []
        for target in self.targets:
            if Covid19API.is_target(target, targets):
                output.append(metrics[target])
        return output


app = Flask("test")
g_covid19api = Covid19API()


@app.route("/")
def index():
    return "OK"


@app.route("/search", methods=["POST"])
def grafana_search():
    global g_covid19api
    targets = g_covid19api.targets
    logging.debug(f'/search: {json.dumps(targets, indent=4, sort_keys=True)}')
    return json.dumps(targets)


@app.route("/query", methods=["POST"])
def grafana_query():
    global g_covid19api
    req = request.get_json(force=True)
    # max_data_points = req['maxDataPoints']
    # interval = req['interval']
    start_time = req['range']['from']
    end_time = req['range']['to']
    targets = [(entry['target'], entry['type']) for entry in req['targets']]
    logging.info(f'/query - {targets} ({start_time}/{end_time}')
    metrics = g_covid19api.get_data(targets, start_time, end_time)
    logging.debug(f'/query: {json.dumps(metrics, indent=4, sort_keys=True)}')
    return json.dumps(metrics)


def covid19api(configuration):
    global g_covid19api, app
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG if configuration.debug else logging.INFO)
    logging.info(f'Starting covid19api v{version}')
    logging.info(f'Configuration: {print_configuration(configuration)}')
    g_covid19api.set_covidpg(CovidPGConnector(
        configuration.postgres_host, configuration.postgres_port,
        configuration.postgres_database,
        configuration.postgres_user, configuration.postgres_password))
    waitress.serve(app, host='0.0.0.0', port=configuration.port)  # nosec


if __name__ == '__main__':
    g_covid19api.set_covidpg(CovidPGConnector(
        os.getenv('POSTGRES_HOST'),
        os.getenv('POSTGRES_PORT'),
        os.getenv('POSTGRES_DATABASE'),
        os.getenv('POSTGRES_USER'),
        os.getenv('POSTGRES_PASSWORD')))
    cProfile.run('g_covid19api.get_data([("confirmed","timeseries")])')
