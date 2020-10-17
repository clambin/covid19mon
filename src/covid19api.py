import os
import cProfile
import json
import logging
from datetime import datetime
from src.covidpgconnector import CovidPGConnector
from src.version import version
from src.configuration import print_configuration

from flask import Flask, request


class Covid19API:
    def __init__(self):
        self._targets = ['confirmed', 'death', 'recovered', 'active']
        self.covid19pg = None
        self._epochs = {}

    @property
    def targets(self):
        return self._targets

    def set_covidpg(self, covidpg):
        self.covid19pg = covidpg

    def get_data(self, targets):
        def datetime_to_epoch(ts):
            if ts not in self._epochs:
                self._epochs[ts] = \
                    int((datetime(ts.year, ts.month, ts.day) - datetime(1970, 1, 1)).total_seconds() * 1000)
            return self._epochs[ts]

        def is_target(my_target, target_names):
            for t in target_names:
                if t[0] == my_target:
                    return True
            return False

        def get_data_by_time_country():
            my_countries = set()
            my_values = dict()
            for entry in self.covid19pg.list():
                time = datetime_to_epoch(entry[0])
                code = entry[1]
                confirmed = entry[3]
                death = entry[4]
                recovered = entry[5]
                if time not in my_values:
                    my_values[time] = dict()
                if code not in my_values[time]:
                    my_values[time][code] = {}
                my_values[time][code] = {'confirmed': confirmed, 'death': death, 'recovered': recovered}
                my_countries.add(code)
            return my_values, my_countries

        # TODO: support table output: https://grafana.com/grafana/plugins/simpod-json-datasource#query
        def get_data_by_time(my_values, my_countries):
            my_metrics = dict()
            for t in self.targets:
                my_metrics[t] = {'target': t, 'datapoints': []}
            last = {
                'confirmed': {country: 0 for country in my_countries},
                'death': {country: 0 for country in my_countries},
                'recovered': {country: 0 for country in my_countries}
            }
            for time, time_data in my_values.items():
                for country, data in time_data.items():
                    last['confirmed'][country] = data['confirmed']
                    last['death'][country] = data['death']
                    last['recovered'][country] = data['recovered']
                current = dict()
                current['confirmed'] = sum(last['confirmed'].values())
                current['death'] = sum(last['death'].values())
                current['recovered'] = sum(last['recovered'].values())
                current['active'] = current['confirmed'] - current['death'] - current['recovered']
                for t in self.targets:
                    my_metrics[t]['datapoints'].append([current[t], time])
            return my_metrics

        values, countries = get_data_by_time_country()
        metrics = get_data_by_time(values, countries)
        output = []
        for target in self.targets:
            if is_target(target, targets):
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
    # TODO: optimize by only calculating/returning for start_time/end_time
    # start_time = req['range']['from']
    # end_time = req['range']['to']
    targets = [(entry['target'], entry['type']) for entry in req['targets']]
    logging.info(f'/request - {targets}')
    metrics = g_covid19api.get_data(targets)
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
    app.run(debug=False, host='0.0.0.0')  # nosec


if __name__ == '__main__':
    g_covid19api.set_covidpg(CovidPGConnector(
        os.getenv('POSTGRES_HOST'),
        os.getenv('POSTGRES_PORT'),
        os.getenv('POSTGRES_DATABASE'),
        os.getenv('POSTGRES_USER'),
        os.getenv('POSTGRES_PASSWORD')))
    cProfile.run('g_covid19api.get_data([("confirmed","timeseries")])')
