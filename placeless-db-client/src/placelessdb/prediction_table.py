from placelessdb.common import insert_table
import time
import logging


class Prdiction:
    def __init__(self, connection):
        self.conn = connection

    def insert(self, attributes, values):
        if len(values) == len(attributes) and not all(
                [isinstance(val, tuple) and len(val) == len(attributes) for val in values]):
            insert_table(self.conn, 'Predictions', attributes=attributes, values=values)
        elif all([isinstance(val, tuple) and len(val) == len(attributes) for val in values]):
            insert_table(self.conn, 'Predictions', attributes=attributes, values=values, many=True)
        else:
            logging.debug('Not enough values to insert `Predictions` table...')

    def get_prediction(self, workload_id: tuple, num_of_predictions, conf_int=False):
        """
        Gtting the last predicted value for a workload with an optional confidence interval
        :param workload_id: tuple of workload id (workload_name,namespace)
        :param conf_int: bool, True for getting the confidence interval and False for otherwise
        :return: list
        """

        curr = self.conn.cursor()
        workload_name, namespace = workload_id
        if conf_int:
            query = f"""SELECT
                        cpu_pred, mem_pred,lower_cpu_confi,upper_cpu_confi,lower_mem_confi,upper_mem_confi
                        FROM 
                            Predictions 
                        WHERE 
                            workload_name = '{workload_name}'
                            AND 
                            namespace = '{namespace}'
                        ORDER BY 
                            pridicted_TS DESC LIMIT {num_of_predictions}"""
        else:

            query = f"""SELECT
                            cpu_pred, mem_pred 
                        FROM 
                            Predictions 
                        WHERE 
                            workload_name = '{workload_name}'
                            AND 
                            namespace = '{namespace}'
                        ORDER BY 
                            pridicted_TS DESC LIMIT {num_of_predictions}"""
        try:
            curr.execute(query)
            result_set = curr.fetchall()
            result_set = [row for row in result_set]
            curr.close()
            return result_set
        except Exception as err:
            logging.error(f"Trying to get predictions failed\nError: {err}")
            curr.close()

    def get_resource_range(self, workload_id=(), all=False):
        """
        Getting a range of values that is recommend for request and limit values for cpu and memory
        :param workload_id: tuple of workload id (workload_name,namespace) or multiple tuples of workload id
        :param all: bool, True for getting for all workloads and False for otherwise
        :return:
        """
        curr = self.conn.cursor()
        earlier = time.time() - 300  # 5 min ego
        if all:
            query = f"""SELECT 
                            min(lower_cpu_confi), CPU_request,
                            max(upper_cpu_confi), CPU_limit, 
                            min(lower_mem_confi), memory_request ,
                            max(upper_mem__confi),memory_limit, 
                            Predictions.workload_id,
                            max(cpu_pred), max(mem_pred)
                        FROM 
                            Predictions JOIN  Workload 
                            ON 
                                Predictions.workload_name = Workload.workload_name 
                                AND
                                Predictions.namespace = Workload.namespace
                                    
                        WHERE
                            predicted_TS > {earlier} 
                        GROUP BY 
                            Predictions.namespace,Predictions.workload_name """
        elif isinstance(id, tuple) and len(workload_id) > 2:
            # str_ids = str(tuple([str(i) for i in id]))
            query = f"""SELECT 
                            min(lower_cpu_confi),CPU_request ,max(upper_cpu_confi), CPU_limit, min(lower_mem_confi),memory_request ,max(upper_mem__confi),memory_limit, id
                        FROM 
                            Predictions JOIN  Workload 
                            ON 
                                Predictions.workload_name = Workload.workload_name 
                                AND
                                Predictions.namespace = Workload.namespace
                        WHERE
                            predicted_TS > {earlier}
                            AND 
                            (Predictions.workload_name,Predictions.namespace) IN {workload_id}
                        GROUP BY 
                            Predictions.namespace,Predictions.workload_name"""
        else:
            workload_name, namespace = workload_id

            query = f"""SELECT 
                            min(lower_cpu_confi),CPU_request ,max(upper_cpu_confi), CPU_limit, min(lower_mem_confi),memory_request max(upper_mem__confi),memory_limit
                        FROM 
                            Predictions JOIN  Workload 
                            ON 
                                Predictions.workload_name = Workload.workload_name 
                                AND
                                Predictions.namespace = Workload.namespace
                        WHERE
                            predicted_TS > {earlier} 
                            AND 
                            Predictions.workload_name = '{workload_name}'
                            AND
                            Predictions.namespace = '{namespace}'"""
        try:
            curr.execute(query)
            result_set = curr.fetchall()  # returning tuple inside list [()]
            result_set = [row for row in result_set]
            curr.close()
            return result_set
        except Exception as err:
            logging.error(f"Trying to get resource range failed\nError: {err}")
            curr.close()

    def clear_data(self, workload_id=None, all=False):
        workload_name, namespace = workload_id
        last_week_ts = time.time() - 60 * 60 * 24 * 7
        curr = self.conn.cursor()
        if all:
            query = f"""DELETE
                        FROM
                            Predictions

                        WHERE
                            predicted_TS < '{last_week_ts}'
                                """
        else:

            query = f"""DELETE
                        FROM
                            WORKLOAD_USAGE
        
                        WHERE
                            workload_name = '{workload_name}' 
                            AND 
                            namespace = '{namespace}'
                            AND
                            predicted_TS < '{last_week_ts}'
                                """
        try:
            curr.execute(query)
            self.conn.commit()
            curr.close()
        except Exception as err:
            logging.error(f"Trying to set resources to workload failed\nError: {err}")
            curr.close()
