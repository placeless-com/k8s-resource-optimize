from placelessdb.common import insert_table
import logging


class Update:
    def __init__(self, connection):
        self.conn = connection

    def insert(self, attributes, values: list):
        """
        Example:
        pdb = PDB()
        pdb.Updates.insert(attributes=('workload_name','cpu_request','cpu_limit','memory_request','memory_limit',namespace1),
         values=([('workload_name1',1,2,3,4,namespace1),('workload_name2',5,6,7,8,namespace2)]))

        :param attributes: tuple
        :param values: list
        :return: None
        """
        if len(values) == len(attributes) and not all(
                [isinstance(val, tuple) and len(val) == len(attributes) for val in values]):
            insert_table(self.conn, 'Updates', attributes=attributes, values=values)
        elif all([isinstance(val, tuple) and len(val) == len(attributes) for val in values]):
            insert_table(self.conn, 'Updates', attributes=attributes, values=values, many=True)
        else:
            logging.debug('Not enough values to insert `Updates` table...')

    def get_workloads_to_update(self):
        """
        getting the all workload's id (name,namespace) from update table
        :return: list
        """
        curr = self.conn.cursor()
        query = f"""SELECT 
                        workload_name, namespace
                    FROM 
                        Updates"""
        try:
            curr.execute(query)
            result_set = curr.fetchall()
            result_set = [row for row in result_set]
            curr.close()
            return result_set
        except Exception as err:
            logging.error(f"Trying to get records from Update table failed\n Error: {err}")
            curr.close()

    def get_updates(self):
        """
        getting all the updates needed from the updates table
        :return: list
        """
        curr = self.conn.cursor()
        query = f"""SELECT *
                    FROM 
                        Updates"""
        try:
            curr.execute(query)
            result_set = curr.fetchall()
            result_set = [row for row in result_set]
            curr.close()
            return result_set
        except Exception as err:
            curr.close()
            logging.error(f"Trying to get records from Update table failed\n Error: {err}")

    def case_generator(self, workload_id: tuple, cpu_request: list, cpu_limit: list, memory_request: list,
                       memory_limit: list):
        """
        generates parts of `case` for the update method
        :param workload_id: list of workloads need to be updated
        :return:
        """
        num_of_updates = len(workload_id)
        cols = {"cpu_request": cpu_request, "cpu_limit": cpu_limit, "memory_request": memory_request,
                "memory_limit": memory_limit}
        set = "SET "
        for col_name, col in cols.items():
            cases = f"{col_name} = (CASE "
            for i in range(num_of_updates):
                cases += f"WHEN (workload_name,namespace) = {workload_id[i]} THEN {col[i]} "
            set += cases
            set += "),"
        set = set[:-1]
        return set

    def update(self, workload_id: tuple, cpu_request, cpu_limit, memory_request, memory_limit):
        """
        updates the request & limit values in the table

        :param workload_id: tuple of workloads need to be updated
        :return: None
        """
        if isinstance(workload_id, tuple) and len(workload_id) > 0:
            curr = self.conn.cursor()
            if len(workload_id) == 2 and isinstance(workload_id[0], str) and isinstance(workload_id[1], str):
                workload_name, namespace = workload_id
                query = f"""UPDATE 
                                Updates
                            SET
                                cpu_request = {cpu_request},
                                cpu_limit = {cpu_limit},
                                memory_request = {memory_request},
                                memory_limit = {memory_limit}
                            WHERE
                                workload_name = '{workload_name}'
                                AND 
                                namespace = '{namespace}'
                
                                """
            elif len(workload_id) >= 2 and isinstance(workload_id[0], tuple) and isinstance(workload_id[1], tuple):
                query = """UPDATE Updates """ + self.case_generator(workload_id, cpu_request, cpu_limit, memory_request,
                                                                    memory_limit)
            else:
                logging.debug(f"Trying to update the Updates table failed...\ninput {workload_id} was not expected")
                query = " "
            try:
                curr.execute(query)
                self.conn.commit()
                curr.close()
            except Exception as err:
                logging.error(f"Trying to update the Updates table failed...\nError : {err}")
                curr.close()

    def delete(self, workload_id):
        """
        deletes records from the table.

        Example:
        pdb = PDB()
        pdb.Updates.delete(('workload_id1',workload_id2,...))

        :param workload_id:
        :return: None
        """
        curr = self.conn.cursor()
        # If there is only one workload in the tuple it send in as a string
        if isinstance(workload_id, tuple) and len(workload_id) == 2 \
                and isinstance(workload_id[0], str) and isinstance(workload_id[1], str):
            workload_name, namespace = workload_id
            query = f"DELETE FROM Updates  WHERE workload_name = '{workload_name}' AND namespace = '{namespace}'"
        else:
            logging.debug(f"Trying to delete from Updates table failed...\ninput {workload_id} was not expected")
            query = ""
        try:
            curr.execute(query)
            self.conn.commit()
            curr.close()
        except Exception as err:
            print(f"Trying to delete from Updates table failed...\nError : {err}")
            curr.close()
