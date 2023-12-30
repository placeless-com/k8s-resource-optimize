import time
import logging


class Workload:
    def __init__(self, connection):
        self.conn = connection

    def insert(self, workload_json):
        curr = self.conn.cursor()
        query = f"""insert into Workload (workload_name,namespace,creation_TS,creation_Date,CPU_limit,memory_limit,CPU_request,memory_request,AWS_FT,trained) 
                    VALUES('{workload_json["workload_name"]}','{workload_json["namespace"]}',{workload_json["creation_TS"]},'{workload_json["creation_Date"]}',{workload_json["CPU_limit"]},{workload_json["memory_limit"]},{workload_json["CPU_request"]},{workload_json["memory_request"]},'{workload_json["AWS_FT"]}',0)"""
        try:
            curr.execute(query)
            self.conn.commit()
            curr.close()
        except Exception as err:
            logging.error(f"failed to run {query} - {err} ")
            curr.close()

    def get_pk_rec(self, workload_id: tuple):
        """
        Example1:
        pdb = PDB()
        pdb.Workload.get_pk_rec((('workload_name1','namespace1'),('workload_name2','namespace1')))
        Example2:
        pdb = PDB()
        pdb.Workload.get_pk_rec(('workload_name1','namespace2'))

        Getting the full record from Workload table for each workload id

        :param workload_name: tuple of strings (workload_name, namespace) in case only one workload is requested. or multiple tuples.
        :return: list
        """
        curr = self.conn.cursor()
        mul_workloads_query = f"""SELECT * From Workload WHERE (workload_name,namespace) IN {workload_id}"""

        if isinstance(workload_id, tuple) and len(workload_id) == 2:
            if isinstance(workload_id[0], tuple) and isinstance(workload_id[1], tuple):
                query = mul_workloads_query
            elif isinstance(workload_id[0], str) and isinstance(workload_id[1], str):
                workload_name, namespace = workload_id
                query = f"""SELECT * FROM Workload WHERE workload_name = '{workload_name}' AND namespace ='{namespace}'"""
            else:
                logging.debug(f"The parameter passed wrong {workload_id}")
                query = ""
        elif isinstance(workload_id, tuple) and len(workload_id) > 2:
            query = mul_workloads_query
        else:
            logging.debug(f"The parameter passed wrong {workload_id}")
            query = ""
        try:
            curr.execute(query)
            result_set = curr.fetchall()
            result_set = [row for row in result_set]
            curr.close()
            return result_set
        except Exception as err:
            logging.error(f"Trying to get record from Workload table failed\nError: {err}")
            curr.close()
            return None

    def delete(self, workload_id: tuple):
        """
        Delete workloads from the workload table

        :param workload_id:tuple of strings (workload_name, namespace) in case only one workload is requested. or multiple tuples
        :return:
        """
        mul_workloads_query = f"""DELETE FROM Workload WHERE (workload_name,namespce) IN {workload_id}"""
        curr = self.conn.cursor()
        if isinstance(workload_id, tuple) and len(workload_id) == 2:
            if isinstance(workload_id[0], tuple) and isinstance(workload_id[1], tuple):
                query = mul_workloads_query
            elif isinstance(workload_id[0], str) and isinstance(workload_id[1], str):
                workload_name, namespace = workload_id
                query = f"""DELETE FROM Workload WHERE workload_name = '{workload_name}' AND namespace = '{namespace}'"""
            else:
                logging.debug(f"The parameter passed wrong {workload_id}")
                query = ""
        elif isinstance(workload_id, tuple) and len(workload_id) > 2:
            query = mul_workloads_query
        else:
            logging.debug(f"The parameter passed wrong {workload_id}")
            query = ""
        try:
            curr.execute(query)
            self.conn.commit()
            curr.close()
        except Exception as err:
            logging.error(f"Trying to delete from Workload table failed\nError: {err}")
            curr.close()

    def get_workloads_to_retrain(self):
        """
        Get all the workloads by their id(name,namespace) that suffer from model drift(model dose not predict well anymore).
        :return:list of tuples
        """
        curr = self.conn.cursor()
        query = """
                SELECT
                    Workload.workload_name,Workload.namespace
                FROM Workload,Residuals
                WHERE Workload.workload_name = Residuals.workload_name
                    AND Workload.namespace = Residuals.namespace 
                    AND Workload.trained  = TRUE
                    AND Workload.last_train_TS <= Residuals.UTS 
                    AND (Residuals.CPU_MSE /Workload.cpu_request > 0.05 OR Residuals.memory_MSE /Workload.memory_request > 0.05)
                """
        try:
            curr.execute(query)
            result_set = curr.fetchall()
            result_set = [row for row in result_set]
            curr.close()
            return result_set
        except Exception as err:
            logging.error(f"Trying to get workload to retrain failed\nError: {err}")
            curr.close()

    def get_workloads_to_build(self):
        """
        Get all the workloads by their id(name,namespace), that have enough data and `placeless` can fit a model to it.
        :return:list of tuples
        """
        curr = self.conn.cursor()
        query = """SELECT
                        workload_name,namespace  
                    FROM(
                        SELECT
                            WORKLOAD_USAGE.workload_name AS workload_name,
                            WORKLOAD_USAGE.namespace AS namespace, COUNT(*) AS num_of_recs
                        FROM
                            WORKLOAD_USAGE JOIN Workload 
                            ON 
                            WORKLOAD_USAGE.workload_name = Workload.workload_name AND WORKLOAD_USAGE.namespace = Workload.namespace
                        WHERE Workload.trained is False
                        GROUP BY namespace, workload_name
                        HAVING num_of_recs > 100
                        ) AS G_id"""
        try:
            curr.execute(query)
            result_set = curr.fetchall()
            result_set = [row for row in result_set]
            curr.close()
            return result_set
        except Exception as err:
            logging.error(f"Trying to get workload to build failed\nError: {err}")
            curr.close()
            return None

    def get_all_workloads(self, trained: bool):
        """
        Gets all the workloads by their id(name, namespace) from the Workload table
        with an optional to get data about workloads how got a ML model attached

        :param trained: a bool for if to get data for trained(an ML model) workloads only
        :return: tuple
        """
        curr = self.conn.cursor()
        try:
            if trained:
                curr.execute("SELECT workload_name,namespace FROM Workload WHERE Workload.trained is TRUE")
            else:
                curr.execute("SELECT workload_name, namespace FROM Workload")

            result_set = curr.fetchall()
            workloads_name = [name for name in result_set]
            curr.close()
            return workloads_name
        except Exception as err:
            logging.error(f"Trying to get record from Workload table failed\nError: {err}")
            curr.close()

    def get_enabled_workloads(self, trained: bool, enabled: bool):
        curr = self.conn.cursor()
        try:

            curr.execute(f"""
                                SELECT 
                                    Workload.workload_name, Workload.namespace
                                FROM 
                                    Workload JOIN Workload_Status
                                    ON Workload.workload_name = Workload_Status.workload_name
                                    AND Workload.namespace = Workload_Status.namespace
                                WHERE 
                                    Workload_Status.enabled = {enabled} 
                                    AND Workload.trained = {trained}""")

            result_set = curr.fetchall()
            workloads_name = [name for name in result_set]
            curr.close()
            return workloads_name
        except Exception as err:
            logging.error(f"Trying to get record from Workload table failed\nError: {err}")
            curr.close()

    def set_obj_to_trained(self, workload_id: tuple):
        """
        Setting the attribute `trained` to True(so we know the workload has a model fitted to it)

        :param workload_id: single tuple ('workload_name', 'namespace')
        :return:
        """
        curr = self.conn.cursor()
        workload_name, namespace = workload_id
        try:
            query = f"""UPDATE
                        Workload 
                        SET trained = true, last_train_TS={float(time.time())} 
                        WHERE 
                            workload_name= '{workload_name}' AND namespace = '{namespace}'"""
            curr.execute(query)
            self.conn.commit()
            curr.close()
        except Exception as err:
            logging.error(f"Trying to set workload to trained failed\nError: {err}")
            curr.close()

    def set_obj_to_untrained(self, workload_id: tuple):
        """
        Setting the attribute `trained` to True(so we know the workload has a model fitted to it)

        :param workload_id: single tuple ('workload_name', 'namespace')
        :return:
        """
        curr = self.conn.cursor()
        workload_name, namespace = workload_id
        try:
            query = f"""UPDATE
                        Workload 
                        SET trained = FALSE 
                        WHERE 
                            workload_name= '{workload_name}' AND namespace = '{namespace}'"""
            curr.execute(query)
            self.conn.commit()
            curr.close()
        except Exception as err:
            logging.error(f"Trying to set workload to trained failed\nError: {err}")
            curr.close()

    def set_last_train_TS(self, workload_id):
        """
        Setting the current unix timestamp to the last time the model has bin build\retrain
        :param workload_id: tuple of strings (workload_name, namespace)
        :return:
        """
        workload_name, namespace = workload_id
        curr = self.conn.cursor()
        query = f"""UPDATE Workload SET last_train_TS={float(time.time())} 
                    WHERE 
                        workload_name = '{workload_name}' 
                        AND 
                        namespace = '{namespace}'"""
        try:
            curr.execute(query)
            self.conn.commit()
            curr.close()
        except Exception as err:
            logging.error(f"Trying to set training time to workload failed\nError: {err}")
            curr.close()

    def set_resources(self, workload_id: tuple, cpu_req, mem_req, cpu_lim, mem_lim):
        """
        Setting the resources after a change has bin made

        :param workload_id: tuple of strings (workload_name, namespace)
        :param cpu_req: int, new cpu request
        :param mem_req: int, new memory request
        :param cpu_lim: int, new cpu limit
        :param mem_lim: int, new memory limit
        :return:
        """
        workload_name, namespace = workload_id
        curr = self.conn.cursor()
        query = f"""UPDATE
                        Workload
                    SET
                        CPU_request = '{cpu_req}',
                        memory_request = '{mem_req}',
                        CPU_limit = '{cpu_lim}' ,
                        memory_limit = '{mem_lim}' 
                    WHERE
                        workload_name = '{workload_name}' 
                        AND 
                        namespace = '{namespace}'
                            """
        try:
            curr.execute(query)
            self.conn.commit()
            curr.close()
        except Exception as err:
            logging.error(f"Trying to set resources to workload failed\nError: {err}")
            curr.close()
