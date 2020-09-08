import os
import datetime
import requests
import logging
from src.covid19 import country_codes
from src.pgconnector import CovidConnector

# You expect country names & codes would be an easy standard but noooooo ...
country_mapping = {
    'Wallis and Futuna Islands': 'Wallis and Futuna',
    'Republic of Kosovo': 'Kosovo',
    'United States of America': 'US',
    'Holy See (Vatican City State)': 'Holy See',
    'Korea (South)': 'Korea, South',
    'Saint-Martin (French part)': 'Saint Martin',
    'Cocos (Keeling) Islands': 'Cocos [Keeling] Islands',
    'Côte d\'Ivoire': 'Cote d\'Ivoire',
    'Micronesia, Federated States of': 'Micronesia',
    'Palestinian Territory': 'West Bank and Gaza',
    'Russian Federation': 'Russia',
    'Macao, SAR China': 'Macau',
    'ALA Aland Islands': 'Åland',
    'Pitcairn': 'Pitcairn Islands',
    'Brunei Darussalam': 'Brunei',
    'Hong Kong, SAR China': 'Hong Kong',
    'Macedonia, Republic of': 'North Macedonia',
    'Virgin Islands, US': 'U.S. Virgin Islands',
    'Myanmar': 'Burma',
    'Korea (North)': 'North Korea',
    'Saint Vincent and Grenadines': 'Saint Vincent and the Grenadines',
    'Heard and Mcdonald Islands': 'Heard Island and McDonald Islands',
    'Svalbard and Jan Mayen Islands': 'Svalbard and Jan Mayen',
    'Taiwan, Republic of China': 'Taiwan*',
    'Tanzania, United Republic of': 'Tanzania',
    'Syrian Arab Republic (Syria)': 'Syria',
    'Iran, Islamic Republic of': 'Iran',
    'Venezuela (Bolivarian Republic)': 'Venezuela',
    'Viet Nam': 'Vietnam',
    'Falkland Islands (Malvinas)': 'Falkland Islands [Islas Malvinas]',
    'US Minor Outlying Islands': 'U.S. Minor Outlying Islands',
    'Lao PDR': 'Laos',
    'Czech Republic': 'Czechia',
    'Cape Verde': 'Cabo Verde',
    'Swaziland': 'Eswatini',
}


class HistoricalData:
    def __init__(self):
        self.url = 'https://api.covid19api.com'
        self.countries = self._get_countries()

    @staticmethod
    def map_country(name):
        mapped = country_mapping[name] if name in country_mapping else name
        if mapped in country_codes.keys():
            return mapped, country_codes[mapped]
        else:
            return None, None

    def _call(self, endpoint):
        url = f'{self.url}/{endpoint}'
        try:
            response = requests.get(url)
            if response.status_code == 200:
                logging.debug(response.content)
                return response.json()
            else:
                logging.error(f'Failed to get data: {response.status_code} - {response.reason}')
        except requests.exceptions.ConnectionError as e:
            logging.warning(f'Failed to connect to {url}: {e}')
        return None

    def _get_countries(self):
        countries = dict()
        for country in self._call('countries'):
            countries[country['Slug']] = {
                'code': country['ISO2'],
                'country': country['Country'],
            }
        return countries

    def get_country(self, slug):
        return self.countries[slug]['country'] if slug in self.countries else None

    def get_historical_data(self, slug):
        output = dict()
        for entry in self._call(f'total/country/{slug}'):
            output[datetime.datetime.strptime(entry['Date'], '%Y-%m-%dT%H:%M:%SZ')] = {
                'confirmed': entry['Confirmed'],
                'death': entry['Deaths'],
                'recovered': entry['Recovered'],
            }
        return output

    def backfill(self, covidconnector, countries=None):
        if countries is None:
            countries = self.countries.keys()
        for slug in countries:
            country = self.get_country(slug)
            country, code = self.map_country(country)
            logging.info(f'Processing {country}')
            last_date = datetime.datetime(2020, 7, 2)  # covidconnector.get_earliest_date(self.get_country[slug][0])
            entries = self.get_historical_data(slug)
            times = sorted(entries.keys())
            if last_date:
                times = list(filter(lambda x: x < last_date, times))
            for time in times:
                covidconnector.add(
                    code,
                    country,
                    entries[time]['confirmed'],
                    entries[time]['death'],
                    entries[time]['recovered'],
                    time
                )
            logging.info(f'Processed {country}. Added {len(times)} records')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    covid = CovidConnector(
        host='192.168.0.10',
        port='5432',
        database='covid19',
        user='postgres',
        password=os.getenv('COVID_PASSWORD')
    )
    server = HistoricalData()
    server.backfill(covid)
