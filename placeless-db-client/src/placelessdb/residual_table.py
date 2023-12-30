from placelessdb.common import insert_table
import logging

class Residuals:
    def __init__(self, connection):
        self.conn = connection

    def insert(self, attributes: tuple, values: tuple):
        if len(values) == len(attributes) and not all([isinstance(val, tuple) and len(val) == len(attributes) for val in values]):
            insert_table(self.conn, 'Residuals', attributes=attributes, values=values)
        elif all([isinstance(val,tuple) and len(val) == len(attributes) for val in values]):
            insert_table(self.conn, 'Residuals', attributes=attributes, values=values, many=True)
        else:
            logging.debug('Not enough values to insert `Residuals` table...')

    def get_records(self, num_of_rec:int,workload_id:tuple):
        """
        :param num_of_rec: int, max number of records to return
        :param workload_id: tuple of workload id (workload_name,namespace)
        :return: list of record
        """
        curr = self.conn.cursor()
        workload_name, namespace = workload_id
        try:
            query = f"""SELECT * 
                        FROM (
                            SELECT * 
                            FROM 
                                Residuals
                            WHERE 
                                workload_name = '{workload_name}'
                                AND 
                                namespace = '{namespace}'
                            ORDER BY 
                                UTS DESC LIMIT {num_of_rec}
                        ) sub
                        ORDER BY UTS, namespace, workload_name ASC
                        """
            curr.execute(query)
            records = curr.fetchall()
            rows = [row for row in records]
            curr.close()
            return rows

        except Exception as err:
            logging.error(f"Trying to get records from Residuals table failed\nError: {err}")
            curr.close()
            return None


    def get_above_res_worklads(self, res, param): # param = "cpu_MSE" or memory_MSE
        """
        Method returns all the workloads that have MSE grater then threshold.
        :param res:int, threshold of the MSE
        :param param: str, cpu_MSE or memory_MSE
        :return:list
        """
        curr = self.conn.cursor()
        query =f"""
                SELECT 
                    workload_name,namespace 
                FROM 
                    Residuals 
                WHERE 
                    {param} >= {res}"""
        try:
            curr.execute(query)
            result_set = curr.fetchall()
            curr.close()
            result_set = [row for row in result_set]
            return result_set
        except Exception as err:
            logging.error(f"Trying to get workloads above MSE threshold failed\nError: {err}")
            curr.close()
            return None

    def get_residuals(self):
        """
        Calculate the SSE - Sum Squared Error(residuals) for each workload and returns it
        :return: list
        """
        cursor = self.conn.cursor()
        query = fr"""
                    SELECT 
                        SUM(cpu_res) AS cpu_SSE , SUM(memory_res) AS memory_SSE, COUNT(*) AS n, workload_name, namespace
                    FROM(
                        SELECT 
                                POWER(WORKLOAD_USAGE.cpu - Predictions.cpu_pred,2) AS cpu_res, 
                                POWER(WORKLOAD_USAGE.memory - Predictions.cpu_pred,2) AS  memory_res,
                                WORKLOAD_USAGE.workload_name AS workload_name,
                                WORKLOAD_USAGE.namespace AS namespace 
                        FROM 
                                Predictions, Workload, WORKLOAD_USAGE  
                        WHERE
                                Workload.trained = TRUE AND
                                WORKLOAD_USAGE.sample_date BETWEEN (Predictions.predicted_date - '00:00:30')
                                                                    AND 
                                                                    (Predictions.predicted_date + '00:00:30') 
                                AND 
                                WORKLOAD_USAGE.TS > Workload.last_train_TS
                                AND 
                                WORKLOAD_USAGE.worklaod_name = Predictions.workload_name
                                AND 
                                WORKLOAD_USAGE.namespace = Predictions.namespace
                      ) AS diff
                    GROUP BY workload_name, namespace
                """
        try:
            cursor.execute(query)
            result_set = cursor.fetchall()
            result_set = [row for row in result_set]
            cursor.close()
            return result_set

        except Exception as err:
            logging.error(f"Trying to get workloads SSE failed\nError: {err}")
            cursor.close()
