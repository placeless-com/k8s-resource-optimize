from placelessdb.common import insert_table


class Event:
    def __init__(self, connection):
        self.conn = connection

    def insert(self, attributes, values):
        insert_table(self.conn, 'Events', attributes=attributes, values=values)

    def get_updates(self, workload_name, starting_point):
        curr = self.conn.cursor()
        query = f"""SELECT 
                        event_date
                    FROM 
                        Events
                    WHERE 
                                event_TS > {starting_point} AND workload = '{workload_name}'"""
        try:
            curr.execute(query)
            result_set = curr.fetchall()
            result_set = [row for row in result_set]
            curr.close()
            return result_set
        except Exception as err:
            print(err)
            curr.close()
