from datetime import timedelta, datetime
from placelessdb import PDB
from placelessdb.common import close_connection
from mysql import connector
from constants import PDB_ARGS
import time
import logging
import traceback
from S3 import get_workloads_from_S3

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
def predict(lags=10):
    # connect to DB
    db_host, db_user, db_pass, db_name = PDB_ARGS
    pdb = PDB(db_host, db_user, db_pass, db_name)
    logging.info("Prediction job is starting")
    # get all trained workload id
    try:
        logging.info("Getting workloads to predict")
        workloads_ids = pdb.Workload.get_all_workloads(trained=True)
        logging.info(f"Workloads to predict got successfully. The workloads are: {workloads_ids}\n")
    except Exception as e:
        logging.error(f"An error occurred while getting workloads to predict: %s", e)
        logging.error(traceback.format_exc())
        close_connection(pdb.connection)
        raise Exception("Could not get workloads id's to retrain from DB")

    # get the model for each workload
    for id in workloads_ids:
        try:
            logging.info(f"Getting workload {id} objects from S3")
            workload = get_workloads_from_S3(id)
        except Exception as e:
            logging.error(f"An error occurred while getting workloads from S3: %s", e)
            logging.error(traceback.format_exc())
            continue
        t = time.time()
        logging.info(f"Predicting for {id}")
        try:
            cpu_predictions = [workload.cpu_model.predict(n_periods=lags, return_conf_int=True), t]
            mem_predictions = [workload.memory_model.predict(n_periods=lags, return_conf_int=True), t]
            logging.info("Sending predictions to DB")
            predictions_to_db(pdb, workload.get_id(), cpu_predictions, mem_predictions)
        except Exception as e:
            logging.error(f"An error occurred while predicting {workload.get_id()}: %s", e)
            logging.error(traceback.format_exc())
            continue
    close_connection(pdb.connection)
    logging.info("Prediction task Done")

def predictions_to_db(pdb: PDB, id, cpu_predictions, mem_predictions):
    workload_name, namespace = id
    mem_pred, mem_conf_int = mem_predictions[0][0], mem_predictions[0][1]
    cpu_pred, cpu_conf_int = cpu_predictions[0][0], cpu_predictions[0][1]
    pred_timestamp = mem_predictions[1]
    datetime_pred_date = datetime.fromtimestamp(pred_timestamp)
    list_of_list = [(workload_name, float(cpu_pred[0]), float(mem_pred[0]),
                     datetime_pred_date, pred_timestamp,
                     float(cpu_conf_int[0][0]), float(cpu_conf_int[0][1]),
                     float(mem_conf_int[0][0]), float(mem_conf_int[0][1]), namespace)]

    for i in range(1, len(mem_pred)):
        list_of_list.append((workload_name, float(cpu_pred[i]), float(mem_pred[i]),
                             datetime_pred_date + timedelta(minutes=5 * i), pred_timestamp + 300 * i,
                             float(cpu_conf_int[i][0]), float(cpu_conf_int[i][1]),
                             float(mem_conf_int[i][0]), float(mem_conf_int[i][1]), namespace
                             ))
    attributes = ('workload_name', 'cpu_pred', 'mem_pred', 'predicted_date',
                  'predicted_TS', 'lower_cpu_confi', 'upper_cpu_confi', 'lower_mem_confi',
                  'upper_mem__confi', 'namespace')
    logging.info("inserting to DB")
    try:
        pdb.Predictions.insert(attributes, values=tuple(list_of_list))
    except Exception as err:
        logging.error(f"insert to db failed: %s", err)
        logging.error(traceback.format_exc())

