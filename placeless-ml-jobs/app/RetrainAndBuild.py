import time

from placelessdb import PDB
from placelessdb.common import close_connection
from constants import PDB_ARGS
from PodObj.podNode import Pnode
from S3 import send_to_s3, get_workloads_from_S3
from t_sPipline.timeseries import TSP
import numpy as np
import logging
import traceback

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def valid_result_set(result_set):
    """
    Check if the result set from the DB is valid and return it if it is
    :param result_set: what returns from the DB
    :return:
    """
    workload_ids = result_set
    if isinstance(workload_ids, tuple) and len(workload_ids) == 0:
        logging.info("No workloads to build a model to")
        return []

    elif isinstance(workload_ids, tuple) and len(workload_ids) == 2 and isinstance(workload_ids[0], str) \
            and isinstance(workload_ids[1], str):
        # single workload
        workload_id = (workload_ids[0], workload_ids[1])
        workload_ids = [workload_id]
        return workload_ids

    else:
        if isinstance(workload_ids, list):
            for workload_id in workload_ids:
                if not len(workload_id) == 2 and isinstance(workload_id[0], str) and isinstance(workload_id[1], str):
                    raise Exception(f"Build model got unexpected results from DB! "
                                    f"Expected list of tuples in the structure "
                                    f"of: (workload_name, namespace), got {workload_ids}")

        else:
            raise Exception(f"Build model got unexpected results from DB! "
                            f"Expected list of tuples in the structure "
                            f"of: (workload_name, namespace), got {workload_ids}")

    return workload_ids


def build_model():
    db_host, db_user, db_pass, db_name = PDB_ARGS
    pdb = PDB(db_host, db_user, db_pass, db_name)
    logging.info("Build job is starting")
    # getting the workload id's as tuple of tuples
    logging.info("Getting the workloads that need a fitted model...")
    try:
        workload_ids = pdb.Workload.get_workloads_to_build()
    except Exception as e:
        logging.error(f"An error occurred while getting workloads to train: %s", e)
        logging.error(traceback.format_exc())
        close_connection(pdb.connection)
        raise Exception("Could not get workloads id's to train from DB")
    # Validate types and structure from DB...
    workload_ids = valid_result_set(result_set=workload_ids)

    # Building phase...

    for id in workload_ids:
        logging.info(f"Starting to build models for {id}")
        try:
            logging.info(f"Fetching workload's object from S3...")
            workload = get_workloads_from_S3(id)
        except Exception as e:
            logging.error(f"An error occurred while fetching the workload {id} from S3: %s", e)
            logging.error(traceback.format_exc())
            workload = Pnode(id)

        try:
            logging.info(f"Fetching workload's data from DB...")
            all_data = pdb.WorkloadUsagAvg.get_records(worklod_id=id, all_records=False, num_of_rec=100, as_json=True)
            logging.info(f"Got data successfully!")
        except Exception as e:
            logging.error(f"An error occurred while building model for {workload.get_id()},"
                          f" could not get the data from DB : %s", e)
            logging.error(traceback.format_exc())
            continue
        for param in ['cpu', 'memory']:
            logging.info(f"Starting to fit a {param} model for {workload.get_id()}")
            try:
                data = all_data[param]
                train_size = int(len(data) * 0.95)
                train, test = data[:train_size], data[train_size:]
                arima_model = first_train('Arima', train)
                set_model(param, workload, model=arima_model)
                logging.info(f"{param} model for {workload.get_id()} has been built successfully!")

            except Exception as e:
                logging.error(f"An error occurred while fitting {param} data to the workload {workload.get_id()}: %s",
                              e)
                logging.error(traceback.format_exc())
                continue
        logging.info(f"Both cpu and memory models for {workload.get_id()} has been built and is now uploaded to S3")
        try:
            send_to_s3(obj=workload)
            logging.info(f" {workload.get_id()} has been uploaded to S3 successfully!")
        except Exception as e:
            logging.error(f"An error occurred while sending {workload.get_id()} to S3: %s", e)
            logging.error(traceback.format_exc())
            continue

        try:
            logging.info(f"Setting {workload.get_id()} to trained...")
            pdb.Workload.set_obj_to_trained(id)
            logging.info(f" {workload.get_id()} has been set to trained in the DB successfully!")
        except Exception as e:
            logging.error(f"An error occurred while sending {workload.get_id()} to S3: %s", e)
            logging.error(traceback.format_exc())
            continue

    pdb.connection.close()
    return


def retrain():
    pdb = PDB(PDB_ARGS)
    retrained_workloads = []
    logging.info("Retrain job is starting")
    try:
        logging.info("Getting workloads to retrain")
        workload_ids = pdb.Workload.get_all_workloads(trained=True)
    except Exception as e:
        logging.error(f"An error occurred while getting workloads to retrain: %s", e)
        logging.error(traceback.format_exc())
        close_connection(pdb.connection)
        raise Exception("Could not get workloads id's to retrain from DB")

    workload_ids = valid_result_set(result_set=workload_ids)
    for id in workload_ids:
        try:
            # add the workload to a retrained list
            retrained_workloads.append(id)
            workload_obj = get_workloads_from_S3(id)
            new_data = pdb.WorkloadUsagAvg.get_records(id=id, from_last_traind=True, as_json=True)
            logging.info('Start update...')
            logging.info('Update for cpu model...')
            start_update_time = time.time()
            workload_obj.cpu_model.update(new_data["cpu"])
            logging.info('Update for memory model...')
            workload_obj.memory_model.update(new_data["memory"])
            logging.info('End update...')
            end_update_time = time.time() - start_update_time
            try:
                if end_update_time > 0.5 * 60:
                    logging.info("Update time takes too long, clearing data")
                    pdb.Workload.set_obj_to_untrained(workload_id=id)
                    pdb.WorkloadUsagAvg.clear_data(id)
                    pdb.Predictions.clear_data(id)
            except Exception as e:
                logging.error(f"Clearing data for {id} failed: %s", e)
                logging.error(traceback.format_exc())
            logging.info(f'Start send {workload_obj.get_id()} to S3...')
            send_to_s3(obj=workload_obj)
            logging.info(f'Finished to send {workload_obj.get_id()} to S3...')
            pdb.Workload.set_last_train_TS(id)
        except Exception as e:
            logging.error(f"Retrain failed for workload {id}: %s", e)
            logging.error(traceback.format_exc())
            continue
        close_connection(pdb.connection)
        return


## all function in this buondry connected to the "build_model" function
def rolling_forcast_test(sampels, pipline):
    pred_list = []
    sse = 0
    for s in sampels:
        pred = pipline.predict(n_periods=1)
        pred_list.append(pred)
        pipline.update(s)
        sse += abs(float(s) - pred)
    mse = sse / len(sampels)
    print(f"MSE: {mse}")
    test_res = mse < np.array(sampels).std()
    print(f"MSE: {mse} std : {np.array(sampels).std()}")
    return mse, test_res


def set_model(param, workload, model):
    if param == 'cpu':
        workload.set_cpu_model(model)
    elif param == 'memory':
        workload.set_memory_model(model)


def return_model(param, workload):
    if param == 'cpu':
        return workload.cpu_model
    elif param == 'memory':
        return workload.memory_model


def first_train(alg, data):
    if alg == 'Arima':
        arima_pipeline = TSP()
        arima_pipeline.process_pipline(data)
        arima_pipeline.fit_data(data)
        return arima_pipeline.model
    elif alg == 'Sarima':
        period = 12  # an hour back
        sarima_pipeline = TSP(seasonal=True, seasonal_period=period)
        sarima_pipeline.process_pipline(data)
        sarima_pipeline.fit_data(data)
        return sarima_pipeline.model
