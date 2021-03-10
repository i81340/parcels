import concurrent.futures
import datetime
import json
import logging
import time
import uuid
import boto3
import shapely.wkt
from tokenizer import Tokenizer


class LoggingSystemLogger:
    # Connect to the elastic cluster

    def __init__(self, product_name, fields_to_tokenize):
        self.cloudwatch = boto3.client('logs')
        self.log_group_name = 'logging-system'
        self.product_name = product_name
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.logs = []
        self.internal_logs = []
        self.logger = logging.getLogger(product_name)
        self.logger.setLevel(logging.INFO)
        self.fields_to_tokenize = fields_to_tokenize
        self.logger.info("LoggingSystemLogger created")

    @staticmethod
    def get_now():
        return int(round(time.time() * 1000))

    @staticmethod
    def get_consumer_from_event( event):
        headers = event.get('request_headers', None)
        consumer_id = None
        if headers is None:
            headers = event.get('headers', None)
        if headers is not None:
            consumer_id = headers.get('x-consumer-custom-id', None)
            if consumer_id is None:
                consumer_id = headers.get('X-Consumer-Custom-ID', None)
        return consumer_id

    @staticmethod
    def get_client_ip_from_event(event):
        headers = event.get('request_headers', None)
        address = None
        if headers is None:
            headers = event.get('headers', None)
        if headers is not None:
            address = headers.get('client-ip-address', None)
        return address

    def tokenize_query_confidential_params(self, query):
        if query is not None:
            try:
                params = query
                if '?' in params:
                    params = params.split('?')[1]
                query_split = params.split('&')
                tokenized_query = ''
                for param in query_split:
                    param_split = param.split('=')
                    param_name = param_split[0]
                    param_value = param_split[1]
                    # if param_name == 'street' or param_name == 'postal':
                    if self.fields_to_tokenize[param_name] is not None:
                        param_value = Tokenizer.tokenize(param_value)
                    tokenized_query += param_name + '=' + param_value + '&'
                return tokenized_query[:-1]
            except:
                return None
        else:
            return None

    def log_event(self, event, success, request_time, args, request_id, status_code, message="", service=""):
        try:
            self.logger.info('Logging event in logging system')
            uri = event.get('request_uri', None)
            query = event.get('queryStringParameters', None)
            if query is None and uri is not None:
                query = uri.split('?')[1]
                uri = uri.split('?')[0]
            headers = event.get('request_headers', None)
            host = None

            if headers is not None:
                host = headers.get('host', None)
            if uri is None:
                uri = event.get('path', None)
            if headers is None:
                headers = event.get('headers', None)
            if host is None and headers is not None:
                host = headers.get('X-Forwarded-Host', None)

            params = json.dumps({
                'url': f'https://{host}{uri}',
                'query': self.tokenize_query_confidential_params(query)
            })

            client = self.get_consumer_from_event(event)
            client_ip_address = self.get_client_ip_from_event(event)
            centroid = {
                "lat": args.lat,
                "lon": args.lng
            }
            self.log(request_id, params, request_time, client, client_ip_address, success, centroid,
                'ImageryProxy', status_code, message, service)
            self.logger.info('Successfully logged request in logging system!')
        except Exception as error:
            self.logger.error(f'{error}')

    def log_from_url(self, request_id, url, init_time, end_time, client, client_ip_address, success, wkt, provider,
                     service, status_code=200, message=""):
        try:
            self.logger.info(f'Logging {provider} request into Logging System with id: {request_id}')
            urlSplited = url.split('?')
            url = urlSplited[0]
            query = self.tokenize_query_confidential_params(urlSplited[1])
            parameters = json.dumps({
                "url": url,
                "query": query
            })

            avg_time = end_time - init_time
            geometry = shapely.wkt.loads(wkt)

            ## Get centroid from polygon requested
            if wkt.__contains__('POLYGON'):
                geometry = geometry.centroid
            coordinates = geometry.coords[0]

            # Build centroid parameters for logging
            centroid = {
                "lat": coordinates[1],
                "lon": coordinates[0]
            }
            # Log into logging system
            self.log(request_id, parameters, avg_time, client, client_ip_address, success, centroid, provider,
                     status_code, message, service)
        except Exception as error:
            self.logger.error(f'{error}')

    def log(self, request_id, parameters, request_time, client, client_ip_address, success, centroid, provider, status_code,
            message, service):
        self.log_async(request_id, parameters, request_time, client, client_ip_address, success, centroid, provider, status_code,
                  message, service)

    def log_async(self, request_id, parameters, request_time, client, client_ip_address, success, centroid, provider, status_code,
                  message, service):

        millis = int(round(time.time() * 1000))
        formated_date_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        tokenized_client = Tokenizer.tokenize(client)
        event = {
            "request_id": request_id,
            "provider": provider,
            "parameters": parameters,
            "sync_response_time": request_time,
            "client": tokenized_client,
            "client_ip": client_ip_address,
            "success": success,
            "request_centroid": centroid,
            "request_date": formated_date_time,
            "product": self.product_name,
            "status_code": status_code,
            "message": message,
            "service": service
        }

        # print(event)
        self.logs.append({
            "timestamp": millis,
            "message": json.dumps(event)
        })

    def push_logs(self):
        """
        Pushes stored logs in 'logs' array to CloudWatch in one single request.
        """
        try:
            log_id = uuid.uuid4()
            formated_date_time_for_log_name = datetime.datetime.now().strftime("%Y-%m-%d")
            stream_name_pre = self.product_name.upper()
            stream_name = f'{stream_name_pre}-{formated_date_time_for_log_name}-{log_id.__str__()}'

            self.logger.info(f'pushing {len(self.logs)} logs to Logging system!')

            try:
                self.logger.info(f'Creating log stream: {stream_name}')
                self.cloudwatch.create_log_stream(
                    logGroupName=self.log_group_name,
                    logStreamName=stream_name
                )
            except:
                self.logger.info('Log stream already exists')

            self.cloudwatch.put_log_events(
                logGroupName=self.log_group_name,
                logStreamName=stream_name,
                logEvents=logs
            )
            self.logger.info('Successfully pushed logs to cloudwatch')
        except:
            self.logger.error('Error logging into logging system')

        self.logs = []
