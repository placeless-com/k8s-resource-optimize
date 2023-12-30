from placelessdb.common import insert_table, close_connection
from placelessdb import PDB
from constants import PDB_ARGS
import mysql.connector
import time
import datetime

def calc_res():
    pdb = PDB(PDB_ARGS)
    try:
        res = pdb.Residuals.get_residuals()
        dic = {}
        for r in res:
                dic[r[3]] = {}
                dic[r[3]]['count'] = r[2]
                dic[r[3]]['SSE_cpu'] = r[0]
                dic[r[3]]['SSE_mem'] = r[1]
                dic[r[3]]['timestamp'] = time.time()
                dic[r[3]]['date'] = datetime.datetime.now()

        insert_tuples = []
        for item in dic.items():
            id = item[0]
            val = item[1]
            val['MSE_cpu'] = val['SSE_cpu'] / max((val['count']-2), 1)
            val['MSE_mem'] = val['SSE_mem'] / max((val['count']-2), 1)

            insert_tuples.append((val['timestamp'], val['date'], val['MSE_cpu'], val['MSE_mem'], id[0]))
        pdb.Residuals.insert(('batch_TS', 'batch_date', 'cpu_MSE', 'memory_MSE', 'id'), tuple(insert_tuples))
        print("Residuals Done.")
    except Exception as err:
        print(err)
        close_connection(pdb.connection)
        
