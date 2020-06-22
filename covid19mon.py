import json
import logging
import time
import os
import requests
from prometheus_client import start_http_server, Summary, Gauge
from pimetrics.probe import APIProbe

REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request', ['server', 'endpoint'])
GAUGES = {
    'corona_confirmed_count':
        Gauge('corona_confirmed_count', 'Number of confirmed cases', ['country_code', 'country_name']),
    'corona_death_count':
        Gauge('corona_death_count', 'Number of deaths', ['country_code', 'country_name']),
    'corona_recovered_count':
        Gauge('corona_recovered_count', 'Number of recoveries', ['country_code', 'country_name']),
}

country_codes = {
    'Andorra': 'AD',
    'United Arab Emirates': 'AE',
    'Afghanistan': 'AF',
    'Antigua and Barbuda': 'AG',
    'Anguilla': 'AI',
    'Albania': 'AL',
    'Armenia': 'AM',
    'Netherlands Antilles': 'AN',
    'Angola': 'AO',
    'Antarctica': 'AQ',
    'Argentina': 'AR',
    'American Samoa': 'AS',
    'Austria': 'AT',
    'Australia': 'AU',
    'Aruba': 'AW',
    'Åland': 'AX',
    'Azerbaijan': 'AZ',
    'Bosnia and Herzegovina': 'BA',
    'Barbados': 'BB',
    'Bangladesh': 'BD',
    'Belgium': 'BE',
    'Burkina Faso': 'BF',
    'Bulgaria': 'BG',
    'Bahrain': 'BH',
    'Burundi': 'BI',
    'Benin': 'BJ',
    'Saint-Barthélemy': 'BL',
    'Bermuda': 'BM',
    'Brunei': 'BN',
    'Bolivia': 'BO',
    'Bonaire, Sint Eustatius, and Saba': 'BQ',
    'Brazil': 'BR',
    'Bahamas': 'BS',
    'Bhutan': 'BT',
    'Bouvet Island': 'BV',
    'Botswana': 'BW',
    'Belarus': 'BY',
    'Belize': 'BZ',
    'Cabo Verde': 'CV',
    'Canada': 'CA',
    'Cocos [Keeling] Islands': 'CC',
    'Congo [DRC]': 'CD',
    'Central African Republic': 'CF',
    'Congo [Republic]': 'CG',
    'Congo (Brazzaville)': 'CD',
    'Congo (Kinshasa)': 'CD',
    'Switzerland': 'CH',
    'Cote d\'Ivoire': 'CI',
    'Cook Islands': 'CK',
    'Chile': 'CL',
    'Cameroon': 'CM',
    'China': 'CN',
    'Colombia': 'CO',
    'Costa Rica': 'CR',
    'Cuba': 'CU',
    'Cape Verde': 'CV',
    'Curaçao': 'CW',
    'Christmas Island': 'CX',
    'Cyprus': 'CY',
    'Czech Republic': 'CZ',
    'Czechia': 'CZ',
    'Germany': 'DE',
    'Djibouti': 'DJ',
    'Denmark': 'DK',
    'Dominica': 'DM',
    'Dominican Republic': 'DO',
    'Algeria': 'DZ',
    'Ecuador': 'EC',
    'Estonia': 'EE',
    'Egypt': 'EG',
    'Western Sahara': 'EH',
    'Eritrea': 'ER',
    'Spain': 'ES',
    'Ethiopia': 'ET',
    'Finland': 'FI',
    'Fiji': 'FJ',
    'Falkland Islands [Islas Malvinas]': 'FK',
    'Micronesia': 'FM',
    'Faroe Islands': 'FO',
    'France': 'FR',
    'Gabon': 'GA',
    'United Kingdom': 'GB',
    'Grenada': 'GD',
    'Georgia': 'GE',
    'French Guiana': 'GF',
    'Guernsey': 'GG',
    'Ghana': 'GH',
    'Gibraltar': 'GI',
    'Greenland': 'GL',
    'Gambia': 'GM',
    'Guinea': 'GN',
    'Guadeloupe': 'GP',
    'Equatorial Guinea': 'GQ',
    'Greece': 'GR',
    'South Georgia and the South Sandwich Islands': 'GS',
    'Guatemala': 'GT',
    'Guam': 'GU',
    'Guinea-Bissau': 'GW',
    'Guyana': 'GY',
    'Gaza Strip': 'GZ',
    'Hong Kong': 'HK',
    'Heard Island and McDonald Islands': 'HM',
    'Honduras': 'HN',
    'Croatia': 'HR',
    'Haiti': 'HT',
    'Hungary': 'HU',
    'Indonesia': 'ID',
    'Ireland': 'IE',
    'Israel': 'IL',
    'Isle of Man': 'IM',
    'India': 'IN',
    'British Indian Ocean Territory': 'IO',
    'Iraq': 'IQ',
    'Iran': 'IR',
    'Iceland': 'IS',
    'Italy': 'IT',
    'Jersey': 'JE',
    'Jamaica': 'JM',
    'Jordan': 'JO',
    'Japan': 'JP',
    'Kenya': 'KE',
    'Kyrgyzstan': 'KG',
    'Cambodia': 'KH',
    'Kiribati': 'KI',
    'Comoros': 'KM',
    'Saint Kitts and Nevis': 'KN',
    'North Korea': 'KP',
    'South Korea': 'KR',
    'Korea, South': 'KR',
    'Kuwait': 'KW',
    'Cayman Islands': 'KY',
    'Kazakhstan': 'KZ',
    'Laos': 'LA',
    'Lebanon': 'LB',
    'Saint Lucia': 'LC',
    'Liechtenstein': 'LI',
    'Sri Lanka': 'LK',
    'Liberia': 'LR',
    'Lesotho': 'LS',
    'Lithuania': 'LT',
    'Luxembourg': 'LU',
    'Latvia': 'LV',
    'Libya': 'LY',
    'Morocco': 'MA',
    'Monaco': 'MC',
    'Moldova': 'MD',
    'Montenegro': 'ME',
    'Saint Martin': 'MF',
    'Madagascar': 'MG',
    'Marshall Islands': 'MH',
    'Macedonia [FYROM]': 'MK',
    'North Macedonia': 'MK',
    'Mali': 'ML',
    'Burma': 'MM',
    'Mongolia': 'MN',
    'Macau': 'MO',
    'Northern Mariana Islands': 'MP',
    'Martinique': 'MQ',
    'Mauritania': 'MR',
    'Montserrat': 'MS',
    'Malta': 'MT',
    'Mauritius': 'MU',
    'Maldives': 'MV',
    'Malawi': 'MW',
    'Mexico': 'MX',
    'Malaysia': 'MY',
    'Mozambique': 'MZ',
    'Namibia': 'NA',
    'New Caledonia': 'NC',
    'Niger': 'NE',
    'Norfolk Island': 'NF',
    'Nigeria': 'NG',
    'Nicaragua': 'NI',
    'Netherlands': 'NL',
    'Norway': 'NO',
    'Nepal': 'NP',
    'Nauru': 'NR',
    'Niue': 'NU',
    'New Zealand': 'NZ',
    'Oman': 'OM',
    'Panama': 'PA',
    'Peru': 'PE',
    'French Polynesia': 'PF',
    'Papua New Guinea': 'PG',
    'Philippines': 'PH',
    'Pakistan': 'PK',
    'Poland': 'PL',
    'Saint Pierre and Miquelon': 'PM',
    'Pitcairn Islands': 'PN',
    'Puerto Rico': 'PR',
    'Palestinian Territories': 'PS',
    'West Bank and Gaza': 'PS',
    'Portugal': 'PT',
    'Palau': 'PW',
    'Paraguay': 'PY',
    'Qatar': 'QA',
    'Réunion': 'RE',
    'Romania': 'RO',
    'Serbia': 'RS',
    'Russia': 'RU',
    'Rwanda': 'RW',
    'Saudi Arabia': 'SA',
    'Solomon Islands': 'SB',
    'Seychelles': 'SC',
    'Sudan': 'SD',
    'South Sudan': 'SS',
    'Sweden': 'SE',
    'Singapore': 'SG',
    'Saint Helena': 'SH',
    'Slovenia': 'SI',
    'Svalbard and Jan Mayen': 'SJ',
    'Slovakia': 'SK',
    'Sierra Leone': 'SL',
    'San Marino': 'SM',
    'Senegal': 'SN',
    'Somalia': 'SO',
    'Suriname': 'SR',
    'São Tomé and Príncipe': 'ST',
    'Sao Tome and Principe': 'ST',
    'El Salvador': 'SV',
    'Sint Maarten': 'SX',
    'Syria': 'SY',
    'Swaziland': 'SZ',
    'Eswatini': 'SZ',
    'Turks and Caicos Islands': 'TC',
    'Chad': 'TD',
    'French Southern Territories': 'TF',
    'Togo': 'TG',
    'Thailand': 'TH',
    'Tajikistan': 'TJ',
    'Tokelau': 'TK',
    'Timor-Leste': 'TL',
    'Turkmenistan': 'TM',
    'Tunisia': 'TN',
    'Tonga': 'TO',
    'Turkey': 'TR',
    'Trinidad and Tobago': 'TT',
    'Tuvalu': 'TV',
    'Taiwan': 'TW',
    'Taiwan*': 'TW',
    'Tanzania': 'TZ',
    'Ukraine': 'UA',
    'Uganda': 'UG',
    'U.S. Minor Outlying Islands': 'UM',
    'US': 'US',
    'Uruguay': 'UY',
    'Uzbekistan': 'UZ',
    'Vatican City': 'VA',
    'Holy See': 'VA',
    'Saint Vincent and the Grenadines': 'VC',
    'Venezuela': 'VE',
    'British Virgin Islands': 'VG',
    'U.S. Virgin Islands': 'VI',
    'Vietnam': 'VN',
    'Vanuatu': 'VU',
    'Wallis and Futuna': 'WF',
    'Samoa': 'WS',
    'Kosovo': 'XK',
    'Yemen': 'YE',
    'Mayotte': 'YT',
    'South Africa': 'ZA',
    'Zambia': 'ZM',
    'Zimbabwe': 'ZW',
}


class CoronaStats(APIProbe):
    def __init__(self, api_key):
        super().__init__('https://covid-19-coronavirus-statistics.p.rapidapi.com/')
        self.api_key = api_key
        self.countries = None

    # Uses https://rapidapi.com/KishCom/api/covid-19-coronavirus-statistics
    def call(self, endpoint, country=None):
        with REQUEST_TIME.labels(self.url, endpoint).time():
            result = None
            try:
                headers = {
                    'x-rapidapi-key': self.api_key,
                    'x-rapidapi-host': 'covid-19-coronavirus-statistics.p.rapidapi.com'
                }
                params = {'country': country} if country else None
                response = self.get(endpoint, headers, params=params)
                if response.status_code == 200:
                    result = response.json()
                    logging.debug(json.dumps(result, indent=3))
                else:
                    logging.error("%d - %s" % (response.status_code, response.reason))
            except requests.exceptions.RequestException as err:
                logging.warning(f'Failed to call "{self.url}": "{err}')
            return result

    def report(self, output):
        for country, details in output.items():
            try:
                code = details['code']
                confirmed = details['confirmed']
                GAUGES['corona_confirmed_count'].labels(code, country).set(confirmed)
                deaths = details['deaths']
                GAUGES['corona_death_count'].labels(code, country).set(deaths)
                recovered = details['recovered']
                GAUGES['corona_recovered_count'].labels(code, country).set(recovered)
            except KeyError as err:
                logging.warning(f'Could not find {err}')
                logging.debug(details)

    def measure(self):
        def nonetozero(val):
            return val if val is not None else 0
        output = {}
        stats = self.call('v1/stats')
        for entry in stats['data']['covid19Stats']:
            country = entry['country']
            if country not in country_codes:
                logging.warning(f'Could not find country code for "{country}". Skipping ...')
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


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)
    start_http_server(8080)
    try:
        key = os.environ['API_KEY']
        probe = CoronaStats(key)
        while True:
            probe.run()
            time.sleep(1800)
    except KeyError as e:
        logging.fatal(f'Missed {e}')
        exit(1)
