from placelessdb import PDB
from placelessdb.common import close_connection
import logging
import re
from CONSTANTS import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

DEFAULT_CONTAINER_RESOURCES_MAP = {"limits": {"cpu": "0m", "memory": "0Mi"}, "requests": {"cpu": "0m", "memory": "0Mi"}}
UNIT_REGEX = re.compile(r'(\d+)([a-zA-Z]+)')
UNIT_MAP_FUNCTION = {'cpu': {'m': lambda a: a * 1000000000},
                     'memory': {'Mi': lambda a: a * (1024 ** 2),
                                'Gi': lambda a: a * (1024 ** 3),
                                'Ki': lambda a: a * 1024}}


class WorkloadActions:
    def __init__(self, CPU_UNIT="m", MEM_UNIT="Ki"):
        self.CPU_UNIT = CPU_UNIT
        self.MEM_UNIT = MEM_UNIT

    @staticmethod
    def convert_size(str_num, desired_units: str) -> float:
        """
        the method scale the number to be in a desired_units.
        param str_num:
        param desired_units:
        return: float, the number after being scaled to the desired_units
        """
        unit_map = {"Ki": 1024,
                    "Mi": 1024 ** 2,
                    "Gi": 1024 ** 3,
                    "Ti": 1024 ** 4,
                    "Pi": 1024 ** 5,
                    "m": 1 / 10 ** 3,
                    "n": 1 / 10 ** 9}

        num, unit = WorkloadActions.to_number(str_num)
        # Convert num to the base unit
        base_units_number = num * unit_map[unit]
        # Convert num to the base unit
        scaled_number = base_units_number / unit_map[desired_units]
        return scaled_number

    @staticmethod
    def to_number(str_num):
        """
        method return the number and it's unit.
        param str_num: str, string of number and unit attached
        return: tuple, (number, unit)
        """
        if not isinstance(str_num, str):
            return 0, 'm'
        UNIT_REGEX = re.compile(r'(\d*\.?\d+)([a-zA-Z]+)')
        value, unit = UNIT_REGEX.search(str_num).groups()
        num = float(value)
        return num, unit

    def register_workload(self, args):
        """

        :param args: dict, key --> corresponding to column in WORKLOAD_USAGE table,
                           value --> The value we want to insert to the column.
        :return: dict, key --> "body"(string),
                        value --> {key --> corresponding to column in WORKLOAD_USAGE table
                                  value --> The transformed value we want to insert to the column.}
        """
        db = PDB(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB)
        workload_json = {"workload_name": args['workload_name'], "namespace": args['workload_namespace'],
                         "creation_TS": args['creation_TS'], "creation_Date": args['creation_Date'],
                         "CPU_limit": self.convert_size(args["CPU_limit"], self.CPU_UNIT),
                         "memory_limit": self.convert_size(args["memory_limit"], self.MEM_UNIT),
                         "CPU_request": self.convert_size(args['CPU_request'], self.CPU_UNIT),
                         "memory_request": self.convert_size(args["memory_request"], self.MEM_UNIT),
                         "AWS_FT": "medium"}
        logging.info(workload_json)
        try:
            db.Workload.insert(workload_json)
            close_connection(db.connection)
            logging.info("Successful insert!")
        except Exception as err:
            close_connection(db.connection)
            logging.error(f"Unsuccessful insert!\n {err.with_traceback(err.__traceback__)}")
            raise

    def is_exist(self, args):
        """

        :param args: dict, key --> workload name/namespace (string)
                           value --> The actual workload name/namespace
                    example:
                        {workload_name: app1, workload_namespace : None}
        :return: dict, key --> "body"(string),
                       value --> {key --> workload name/namespace (string)
                                  value --> The actual workload name/namespace}
        """
        db = PDB(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB)
        workload_id = args['workload_name']
        namespace = args['workload_namespace']
        workload_tuple = (workload_id, namespace,)
        result = db.Workload.get_pk_rec(workload_tuple)
        if result:
            logging.info(f"GET request for {workload_tuple} - Success")
            return True
        logging.info(f"'get workload' {workload_id} not found ")
        return False

    def set_resources(self, workload_name, workload_namespace, resources: dict):
        """

        :param resources: keys: requests, limits - sub keys cpu, memory
        :param workload_name:
        :param workload_namespace:
        """
        db = PDB(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB)
        workload_tuple = (workload_name, workload_namespace,)
        try:
            cpu_req = self.convert_size(resources['requests']['cpu'], self.CPU_UNIT)
            mem_req = self.convert_size(resources["requests"]['memory'], self.MEM_UNIT)
            cpu_lim = self.convert_size(resources["limits"]['cpu'], self.CPU_UNIT)
            mem_lim = self.convert_size(resources["limits"]['memory'], self.MEM_UNIT)
            db.Workload.set_resources(workload_tuple, cpu_req, mem_req, cpu_lim, mem_lim)
            close_connection(db.connection)
        except Exception as err:
            close_connection(db.connection)
            logging.error(f"Set resources failed for workload: {workload_tuple}  msg - {err}")

    def delete(self, args):
        """

        :param args: dict, key --> workload name/namespace (string)
                           value --> The actual workload name/namespace
                    example:
                        {workload_name: app1, workload_namespace : None}
        :return: dict, key --> "body"(string),
                       value --> {key --> workload name/namespace (string)
                                  value --> The actual workload name/namespace}
        """
        db = PDB(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB)
        workload_id = args['workload_name']
        namespace = args['workload_namespace']
        workload_tuple = (workload_id, namespace,)
        logging.info(f"Deleting {workload_tuple}")
        try:
            db.Updates.delete(workload_tuple)
            close_connection(db.connection)
            logging.info(f"The workload: {workload_tuple} deleted")
        except Exception as err:
            close_connection(db.connection)
            logging.error(f"Deletion failed for workload: {workload_tuple}  msg - {err.with_traceback()}")


class ResourcesAction:

    def __init__(self, CPU_UNIT="m", MEM_UNIT="Ki"):
        self.CPU_UNIT = CPU_UNIT
        self.MEM_UNIT = MEM_UNIT

    def get_workload_resources(self, workload_name, workload_namespace):
        db = PDB(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB)
        workload_tuple = (workload_name, workload_namespace,)
        logging.info(f"get_workload_resources")
        try:

            data = db.Workload.get_pk_rec(workload_tuple)[-1]
            workload_returned_resources = {"limits": {"cpu": str(int(data[3])) + self.CPU_UNIT,
                                                      "memory": str(int(data[4])) + self.MEM_UNIT},
                                           "requests": {"cpu": str(int(data[5])) + self.CPU_UNIT,
                                                        "memory": str(int(data[6])) + self.MEM_UNIT}}
            close_connection(db.connection)
            return workload_returned_resources

        except Exception as err:
            logging.error(err.with_traceback(err.__traceback__))
            close_connection(db.connection)
            return None
        return return_val

    def get_resources(self):
        db = PDB(MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB)
        return_val = {}
        try:
            data = db.Updates.get_updates()
            for rec in data:
                workload, cpu_request, cpu_limit, mem_request, mem_limit, namespace = rec
                logging.info(f"{workload}, cpu_request, cpu_limit, mem_request, mem_limit, namespace")
                return_val[workload] = {'resources': {
                    'requests':
                        {'cpu': str(cpu_request) + self.CPU_UNIT,
                         'memory': str(mem_request) + self.MEM_UNIT},
                    'limits': {'cpu': str(cpu_limit) + self.CPU_UNIT,
                               'memory': str(mem_limit) + self.MEM_UNIT}},
                    'namespace': namespace}
            close_connection(db.connection)

        except Exception as err:
            logging.error(err.with_traceback(err.__traceback__))
            close_connection(db.connection)
            return None
        return return_val
