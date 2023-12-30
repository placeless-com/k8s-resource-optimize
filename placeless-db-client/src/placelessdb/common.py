from mysql import connector
import logging
import traceback
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def insert_table(conn,table_name, attributes: tuple, values: tuple, many=False):

    def create_attributes_str(attributes: tuple, creation=True):
        string = '('
        for attribute in attributes:
            if creation:
                string += attribute[0] + ' ' + attribute[1] + ', '
            else:
                string += attribute + ', '
        return string[:-2] + ')'

    def get_type_format(num_of_values):
        string = '('
        for _ in range(num_of_values):
            string += '%s, '
        return string[:-2] + ')'

    cursor = conn.cursor()
    attributes_as_str = create_attributes_str(attributes, creation=False)
    vals_format = get_type_format(len(attributes))
    q_struct = f"INSERT INTO {table_name} {attributes_as_str} VALUES {vals_format}"
    try:
        if many:
            cursor.executemany(q_struct, values)
        else:
            cursor.execute(q_struct, values)

        conn.commit()
        cursor.close()
    except Exception as err:
        logging.error(traceback.format_exc())
        logging.error(f"Insert to table {table_name} failed\nError: {err}")
        cursor.close()


def open_connection(params):
    host, user, password, database = params
    return connector.connect(user= user,
                             password=password,
                             host=host,
                             db=database)
def close_connection(conn):
    conn.close()

def get_conn_params():
    conn_param = ["database-placeless.clbd6x8m8o6b.us-east-1.rds.amazonaws.com",
                  "admin", "N0tS0EasyPass!", "placeless"]
    return conn_param