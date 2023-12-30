import logging
import json
import re
import os
import time
from datetime import datetime

from placelessdb import PDB
from placelessdb.common import close_connection
filter_date_pattern = re.compile(r'.*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
MYSQL_HOST = os.environ.get("PLACELESS_MYSQL_HOSTNAME", "localhost")
MYSQL_USER = os.environ.get("PLACELESS_MYSQL_USERNAME", "placeless")
MYSQL_PASSWORD = os.environ.get("PLACELESS_MYSQL_PASSWORD", "password")
MYSQL_DB = os.environ.get("PLACELESS_MYSQL_DB", "placeless")
CPU_UNIT = 'm'
MEMORY_UNIT = 'Ki'


dbhost = os.environ.get('ENDPOINT_ADDRESS', '127.0.0.1')
dbport = os.environ.get('PORT', '3306')
dbname = os.environ.get('DB_NAME', 'placeless')
dbuser = os.environ.get('MASTER_USERNAME', 'placeless')
dbpass = os.environ.get('MASTER_PASSWORD', 'password')
dbtype = os.environ.get('DB_TYPE', 'mysql')


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MetricsProcessor:
    def __init__(self, cluster_name):
        self.cluster_name = cluster_name

    def to_number(self,str_num):
        """
        method return the number and it's unit.
        :param str_num: str, string of number and unit attached
        :return: tuple, (number, unit)
        """
        if not isinstance(str_num, str):
            return 0, 'm'
        UNIT_REGEX = re.compile(r'(\d*\.?\d+)([a-zA-Z]+)')

        var = UNIT_REGEX.search(str_num)
        if hasattr(var, "groups"):
            value, unit = var.groups()
            num = float(value)
            return num, unit
        return float(str_num), 'm'



    def convert_size(self, str_num, desired_units: str) -> float:
        """
        the method scale the number to be in a desired_units.
        :param str_num:
        :param desired_units:
        :return: float, the number after being scaled to the desired_units
        """
        unit_map = {"Ki": 1024,
                    "Mi": 1024 ** 2,
                    "Gi": 1024 ** 3,
                    "Ti": 1024 ** 4,
                    "Pi": 1024 ** 5,
                    "m": 1 / 10 ** 3,
                    "n": 1 / 10 ** 9}

        num, unit = self.to_number(str_num)
        # Convert num to the base unit
        base_units_number = num * unit_map[unit]
        # Convert num to the base unit
        scaled_number = base_units_number / unit_map[desired_units]
        return scaled_number

    def to_date(self, str_date):
        """
        convert string date into date
        :param str_date: str, representing a date in format: '%Y-%m-%d %H:%M:%S'
        :return: datetime.datetime, in format of the str_date in the
        """
        try:
            datetime_object = datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S')
            return datetime_object
        except Exception as err:
            logging.error(f"String date to datetime failed\n Error:\n{err}")
            return None

    def to_unix_time(self, date):
        """
        convert date into unix time
        :param date: datetime.datetime
        :return: float, the unix time of the date
        """
        try:
            unix_time = time.mktime(date.timetuple())
            return unix_time
        except Exception as err:
            logging.error(f"Date to unix time failed\n Error:\n{err}")


    def __return_oredered_metric_data(self, input_data, deployment_name, pod_name, file_datetime):
        """
        in this method we parse the metadata from a given workload
        :param input_data: dict, file from S3
        :param deployment_name: str, name of deployment
        :param pod_name: str, name of pod inside the deployment
        :param file_datetime: str, the date in which the file was sent to S3
        :return: tuple of (unix_time, date, cpu, memory, deployment_name, request_cpu,
                                    request_memory, limit_cpu, limit_memory, namespace)
        """

        request_cpu = self.convert_size(
            str_num=input_data['metadata'][deployment_name]["requests"].get("cpu", f"0{CPU_UNIT}"),
            desired_units=CPU_UNIT)

        request_memory = self.convert_size(
            str_num=input_data['metadata'][deployment_name]["requests"].get("memory", f"0{MEMORY_UNIT}"),
            desired_units=MEMORY_UNIT)

        limit_cpu = self.convert_size(
            str_num=input_data['metadata'][deployment_name]["limits"].get("cpu", f"0{CPU_UNIT}"),
            desired_units=CPU_UNIT)

        limit_memory = self.convert_size(
            str_num=input_data['metadata'][deployment_name]["limits"].get("memory", f"0{MEMORY_UNIT}"),
            desired_units=MEMORY_UNIT)

        namespace = input_data['data_metric'][pod_name]["namespace"]

        memory = self.convert_size(
            str_num=input_data['data_metric'][pod_name]["memory_usage"],
            desired_units=MEMORY_UNIT)


        cpu = self.convert_size(
            str_num=input_data['data_metric'][pod_name]["cpu_usage"],
            desired_units=CPU_UNIT)

        date = self.to_date(file_datetime)
        unix_time = self.to_unix_time(date)
        return unix_time, date, cpu, memory, deployment_name, \
               request_cpu, request_memory, limit_cpu, limit_memory, namespace

    def parse_raw_data(self, input_data, file_datetime):
        """
        :param input_data:
        :return: List of tuple with :(unix_time, date, cpu, memory, deployment_name, request_cpu,
                                                request_memory, limit_cpu, limit_memory, namespace)
        """
        prepared_data_metrics = {}
        input_data = json.loads(input_data)
        logger.info("About to filter input_data")
        logger.debug(f"{input_data}")
        for deployment_name in input_data['metadata'].keys():
            for pod_name in input_data['data_metric'].keys():
                if pod_name.startswith(deployment_name):
                    prepared_data_metrics[deployment_name] = self.__return_oredered_metric_data(input_data, deployment_name, pod_name, file_datetime)
        return prepared_data_metrics.values()


    @staticmethod
    def upload_to_mysql(data):
        logger.info("Uploading to MySQL...")
        pdb = PDB(db_host=MYSQL_HOST, db_name=MYSQL_DB, db_pass=MYSQL_PASSWORD, db_user=MYSQL_USER)
        attributes = ('TS', 'sample_date', 'cpu', 'memory', 'workload_name',
                      'CPU_request', 'memory_request', 'CPU_limit', 'memory_limit','namespace')
        try:
            logger.info(f"About to insert {set(data)} records!")
            print(f"About to insert {set(data)} records!")
            print(f"{type(data)}")
            pdb.WorkloadUsagAvg.insert(attributes=attributes, values=tuple(data))
            close_connection(pdb.connection)
            logger.info("Done to uploading to MySQL")
        except Exception as err:
            logger.info("Connection and cursor closed, fail to upload to MySQL\n")
            logger.error(err)
            close_connection(pdb.connection)
