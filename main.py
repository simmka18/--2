# Task 1 

from jsonschema import validate
from jsonschema.exceptions import ValidationError, SchemaError
from json.decoder import JSONDecodeError
from wsgiref.simple_server import make_server
from wsgiref.validate import validator
from datetime import datetime
from dateutil.parser import parse
import json
import wsgiref.util
from urllib.parse import parse_qs
import pytz


def validate_datediff_data(first_date_t, first_scr_tz, second_date_t, second_scr_tz):
    res = ""
    try:
        if not isinstance(parse(first_date_t), datetime):
            res = "First date/time '" + first_date_t + "' is invalid."
        if not isinstance(parse(second_date_t), datetime):
            res += "Second date/time '" + second_date_t + "' is invalid."
    except (ValueError, OverflowError) as error:
        res = "First or second date/time is invalid: '" + first_date_t + "', '" + second_date_t + "'."
        print('Error: ', error)
        print(error.args)
    else:
        if first_scr_tz not in pytz.all_timezones:
            res += "First timezone '" + first_scr_tz + "' is invalid."
        if second_scr_tz not in pytz.all_timezones:
            res += "Second timezone '" + second_scr_tz + "' is invalid."
    return res


def validate_convert_data(date_time_t, src_tz_t, target_tz_t):
    res = ""
    try:
        if not isinstance(parse(date_time_t), datetime):
            res = "Date/time '" + date_time_t + "' is invalid."
    except (ValueError, OverflowError) as error:
        print('Error: ', error)
        print(error.args)
        res = "Date/time '" + date_time_t + "' is invalid."
    else:
        if src_tz_t not in pytz.all_timezones:
            res += "Timezone '" + src_tz_t + "' is invalid."
        if target_tz_t not in pytz.all_timezones:
            res += "Target timezone '" + target_tz_t + "' is invalid."
    return res


class ClassApp:

    FAVICON = 'favicon.ico'
    HTML_INVALID_TZ = """Invalid timezone: %(tz)s"""
    HTML_TIME = """Time in %(tz)s is %(time)s"""
    DATETIME_FORMAT = "%d.%m.%Y %H:%M:%S"
    DATETIME_TEST_FORMAT = "%d.%m.%Y %H:%M"
    API_V1_CONVERT = "api/v1/convert"
    API_V1_DATEDIFF = "api/v1/datediff"
    DATE = b'date'
    DATA = b'data'
    TZ = b'tz'
    TARGET_TZ = b'target_tz'
    FIRST_DATE = b'first_date'
    SECOND_DATE = b'second_date'
    FIRST_TZ = b'first_tz'
    SECOND_TZ = b'second_tz'

    date_json_schema = {
        "type": "object",
        "properties": {
            "date": {"type": "string"},
            "tz": {"type": "string"},
        },
    }

    data_json_schema = {
        "type": "object",
        "properties": {
            "first_date": {"type": "string"},
            "first_tz": {"type": "string"},
            "second_date": {"type": "string"},
            "second_tz": {"type": "string"},
        },
    }

    def __init__(self, environ_t, t_start_response):
        self.environ_m = environ_t
        self.start_t = t_start_response

    def __iter__(self):

        request_meth = self.environ_m['REQUEST_METHOD']
        applicat_uri = wsgiref.util.application_uri(self.environ_m)
        requ_uri = wsgiref.util.request_uri(self.environ_m, False)
        tz_now = pytz.timezone('GMT')
        datetime_now = datetime.now(tz_now)

        if applicat_uri and requ_uri and requ_uri.startswith(applicat_uri):
            path = requ_uri[len(applicat_uri):]
            if request_meth == 'POST':
                response_body = 'Empty request!'
                if path == self.API_V1_CONVERT or path == self.API_V1_DATEDIFF:
                    try:
                        body_request_size = int(self.environ_m.get('CONTENT_LENGTH', 0))
                    except ValueError:
                        print('ValueError:', ValueError)
                        body_request_size = 0

                    if body_request_size > 0:
                        request_body_s = self.environ_m['wsgi.input'].read(body_request_size)
                        dict_k = parse_qs(request_body_s)

                        #   Проверим все параметры: JSON date, JSON data, tz, target_tz, first_date,
                        #   second_date, first_tz, second_tz
                        if path == self.API_V1_CONVERT:
                            if dict_k.get(self.DATE) and dict_k.get(self.DATE)[0]:
                                date_json = dict_k.get(self.DATE)[0]
                                try:
                                    date_new = json.loads(date_json)
                                    validate(instance=date_new, schema=self.date_json_schema)
                                    src_date = date_new['date']
                                    src_tz = date_new['tz']
                                    if dict_k.get(self.TARGET_TZ) and dict_k.get(self.TARGET_TZ)[0]:
                                        target_tz = dict_k.get(self.TARGET_TZ)[0].decode('utf-8')
                                        date_invalid = validate_convert_data(src_date, src_tz, target_tz)
                                        if date_invalid:
                                            response_body = date_invalid
                                        else:
                                            src_tz_informotion = pytz.timezone(src_tz)
                                            src_datetime = src_tz_informotion.localize(parse(src_date))
                                            if src_tz == target_tz:
                                                response_body = \
                                                    "Timezones are same, date/time in '" + src_tz + "' is " + \
                                                    src_datetime.strftime(self.DATETIME_FORMAT)
                                            else:
                                                target_tz_info = pytz.timezone(target_tz)
                                                new_datetime = src_datetime.astimezone(target_tz_info)
                                                response_body = \
                                                    "Date/time in timezone '" + target_tz + "' is " + \
                                                    new_datetime.strftime(self.DATETIME_FORMAT)
                                    else:
                                        response_body = "'target_tz' post parameter is empty!"
                                except (JSONDecodeError, ValidationError, SchemaError, KeyError) as error:
                                    response_body = "Invalid JSON format of 'date' POST parameter: " + date_json.decode('utf-8')
                                    print('Error: ', error)
                                    print(error.args)

                            else:
                                response_body = "'date' POST parameter is empty!"

                        else: # if request to api/v1/datediff
                            if dict_k.get(self.DATA) and dict_k.get(self.DATA)[0]:
                                data_json = dict_k.get(self.DATA)[0]
                                try:
                                    data_new = json.loads(data_json)
                                    validate(instance=data_new, schema=self.data_json_schema)
                                    first_date = data_new['first_date']
                                    second_date = data_new['second_date']
                                    first_tz = data_new['first_tz']
                                    second_tz = data_new['second_tz']

                                    data_invalid = validate_datediff_data(first_date, first_tz, second_date, second_tz)
                                    if data_invalid:
                                        response_body = data_invalid
                                    else:
                                        first_tz_info = pytz.timezone(first_tz)
                                        second_tz_info = pytz.timezone(second_tz)
                                        first_datetime = first_tz_info.localize(parse(first_date))
                                        second_datetime = second_tz_info.localize(parse(second_date))

                                        if first_datetime == second_datetime and first_tz == second_tz:
                                            response_body = 'Dates/times and timezones are same. Difference is 0 s.'
                                        else:
                                            diff = (first_datetime - second_datetime).total_seconds()
                                            response_body = 'Difference is ' + str(abs(int(diff))) + ' s.'

                                except (JSONDecodeError, ValidationError, SchemaError, KeyError) as error:
                                    response_body = "Invalid JSON format of 'data' POST parameter: " + data_json.decode('utf-8')
                                    print('Error: ', error)
                                    print(error.args)
                            else:
                                response_body = "'data' POST parameter is empty!"

                else: # if invalid POST API
                    response_body = "Invalid API path: '" + requ_uri + "'. You should request '/" + self.API_V1_CONVERT + \
                                    "' or '/" + self.API_V1_DATEDIFF + "' only!"

            elif request_meth == 'GET':
                response_body = self.HTML_TIME % {'tz': 'GMT', 'time': datetime_now.strftime(self.DATETIME_FORMAT)}
                if len(requ_uri) > len(applicat_uri):
                    timezone = path
                    if timezone in pytz.all_timezones:
                        tz_now = pytz.timezone(timezone)
                        datetime_now = datetime.now(tz_now)
                        response_body = self.HTML_TIME % {'tz': timezone, 'time': datetime_now.strftime(self.DATETIME_FORMAT)}
                    elif timezone != self.FAVICON:
                        response_body = self.HTML_INVALID_TZ % {'tz': timezone}

        response_body = response_body.encode('UTF-8')
        status = '200 OK'
        response_headers = [('Content-type', 'text/plain')]
        self.start_t(status, response_headers)
        yield response_body


if __name__ == '__main__':

    validator_app = validator(ClassApp)
    with make_server('', 8000, validator_app) as httpd:
        print("Serving on port 8000...")
        httpd.serve_forever()