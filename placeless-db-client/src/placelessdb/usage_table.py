import time

from placelessdb.common import insert_table
import logging


class WorkloadUsagAvg:
    def __init__(self, connection):
        self.conn = connection

    def insert(self, attributes, values):
        """
        Example:
        pdb = PDB()
        at = ('TS', 'sample_date', 'CPU', 'memory' , 'workload_name' , 'CPU_request' , 'memory_request' , 'CPU_limit' ,
        'memory_limit','namespace')
        vals = ((TS1, date1,1,1, 'workload_name1' ,1,1,1,1,namespace1),
                (TS2, date2,2,2, 'workload_name2',2,2,2,2,namespace2)...)
        pdb.WorkloadUsagAvg.insert(attributes=at,values=vals)

        :param attributes: tuple
        :param values: list
        :return: None
        """
        if len(values) == len(attributes) and not all(
                [isinstance(val, tuple) and len(val) == len(attributes) for val in values]):
            insert_table(self.conn, 'WORKLOAD_USAGE', attributes=attributes, values=values)
        elif all([isinstance(val, tuple) and len(val) == len(attributes) for val in values]):
            insert_table(self.conn, 'WORKLOAD_USAGE', attributes=attributes, values=values, many=True)
        else:
            logging.debug('Not enough values to insert `WORKLOAD_USAGE` table...')

    def get_records(self, worklod_id: tuple, num_of_rec=0, from_last_traind=False, as_json=False, all_records=False):
        """
        get records by workload from WORKLOAD_USAGE table and have optional conditions
        :param worklod_id: tuple of strings (workload_name, namespace)
        :param num_of_rec: int, max number of records that will return from the query
        :param from_last_traind: bool, optional to get the records only from the last time the workload's ML model was build\retrain.
        :param as_json: bool, optional to get the data as a dictionary (type dict)
        :param all_records: bool, optional to get all the records of the workload
        :return: list or dict
        """
        workload_name, namespace = worklod_id
        curr = self.conn.cursor()
        if from_last_traind:
            query = f""" SELECT * 
                        FROM 
                            WORKLOAD_USAGE 
                        WHERE 
                            TS > (SELECT last_train_TS FROM Workload WHERE workload_name = '{workload_name}' AND namespace = '{namespace}')
                            AND workload_name = '{workload_name}'
                            AND namespace = '{namespace}'"""

        elif all_records:
            query = f"""SELECT * 
                        FROM
                            WORKLOAD_USAGE 
                        WHERE 
                            workload_name = '{workload_name}'
                            AND 
                            namespace = '{namespace}' """
        else:
            query = f"""SELECT * 
                        FROM (
                            SELECT * 
                            FROM 
                                WORKLOAD_USAGE 
                            WHERE
                                workload_name = '{workload_name}'
                                AND 
                                namespace = '{namespace}' 
                            ORDER BY TS DESC LIMIT {num_of_rec}
                        ) sub
                        ORDER BY workload_name ASC
                        """
        try:
            curr.execute(query)
            records = curr.fetchall()
            if as_json:
                return self.make_as_json(records)
            rows = [row for row in records]
            curr.close()
            return rows
        except Exception as err:
            logging.error(f"Trying to get records from WORKLOAD_USAGE table failed\nError: {err}")
            curr.close()
            return None

    def make_as_json(self, records):
        """
        Transform the records to dict
        :param records: list of tuple(each tuple is a record)
        :return: dict
        """
        json = {'cpu': [], 'memory': [], 'timestamp': []}
        for row in records:
            json['timestamp'].append(row[0])
            json['cpu'].append(row[2])
            json['memory'].append(row[3])
        return json

    def clear_data(self, workload_id):
        workload_name, namespace = workload_id
        last_week_ts = time.time() - 60 * 60 * 24 * 7
        curr = self.conn.cursor()
        query = f"""DELETE
                    FROM
                        WORKLOAD_USAGE
                    
                    WHERE
                        workload_name = '{workload_name}' 
                        AND 
                        namespace = '{namespace}'
                        AND
                        TS < '{last_week_ts}'
                            """
        try:
            curr.execute(query)
            self.conn.commit()
            curr.close()
        except Exception as err:
            logging.error(f"Trying to set resources to workload failed\nError: {err}")
            curr.close()
