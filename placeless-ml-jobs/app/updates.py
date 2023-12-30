import time

from placelessdb import PDB
from placelessdb.common import close_connection
from constants import PDB_ARGS
import numpy as np
import logging
import traceback
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
def check_recommendations(request_recommendations,current_request):
    cpu_request, memory_request = current_request
    recommended_cpu_request, recommended_memory_request = request_recommendations
    check_cpu = lambda r1, r0: (abs(float(r1) - float(r0))/(float(r0) + np.finfo(np.float64).eps)) * 100 > 5 or abs(r1 - r0) > 1 * 10 ** 9
    check_memory = lambda r1, r0: (abs(float(r1) - float(r0))/(float(r0) + np.finfo(np.float64).eps)) * 100 > 5 or abs(r1 - r0) > 100 * 10 ** 6
    return check_cpu(recommended_cpu_request, cpu_request) or check_memory(recommended_memory_request, memory_request)

def get_workloads_resources(workloads,pdb):
    """
    returns a list dict in the following structure:
    {(workload_name,workload_namespace): (cpu_request, cpu_limit,memory_request,memory_limit)}
    """
    workloads_as_tup = tuple([tuple(workload_id) for workload_id in workloads])
    if len(workloads_as_tup) == 1:
        workloads_as_tup = workloads_as_tup[0]
    workloads_metadata = pdb.Workload.get_pk_rec(workloads_as_tup)
    if workloads_metadata is None:
        raise Exception(f"PK for {workloads} return None ")
    workload_name_pos = 0
    namespace_pos = 10
    cpu_limit_pos = 3
    memory_limit_pos = 4
    cpu_request_pos = 5
    memory_request_pos = 6
    workloads_curr_resources = {(rec[workload_name_pos], rec[namespace_pos]):
                                    (rec[cpu_limit_pos], rec[memory_limit_pos],
                                     rec[cpu_request_pos], rec[memory_request_pos])
                                for rec in workloads_metadata}
    return workloads_curr_resources

def get_workloads_preds(workloads, pdb):
    """
    returns dict in structure {(workload_name,workload_namespace) : (cpu_pred, memory_pred)}
    """
    workload_predictions = {}
    for workload in workloads:
        predictions = pdb.Predictions.get_prediction(tuple(workload),num_of_predictions=10)
        cpu_pred = max([cpu for cpu, memory in predictions])
        memory_pred = max([memory for cpu, memory in predictions])
        workload_predictions[tuple(workload)] = (cpu_pred, memory_pred)
    return workload_predictions

def get_recommendation_for_workload(cpu_prediction, memory_prediction):
    """
    returns tuple with the recommended values for request and limit as follow:
    ((cpu_request, memory_request),(cpu_limit, memory_limit))
    """
    cpu_request_recommendation = cpu_prediction + 0.1 * cpu_prediction
    memory_request_recommendation = memory_prediction + 0.1 * memory_prediction
    cpu_limit_recommendation = cpu_prediction + 0.5 * cpu_prediction
    memory_limit_recommendation = memory_prediction + 0.5 * memory_prediction
    request_recommendations = (cpu_request_recommendation, memory_request_recommendation)
    limit_recommendations = (cpu_limit_recommendation, memory_limit_recommendation)
    return request_recommendations, limit_recommendations

def get_curr_resources_for_workload(workload, workload_resources_dict):
    """
        returns tuple with the resource's state of a workload as follow:
        ((curr_cpu_request, curr_memory_request),(curr_cpu_limit, curr_memory_limit))

    """
    curr_recsources = workload_resources_dict[tuple(workload)]
    cpu_curr_limit, memory_curr_limit, cpu_curr_request, memory_curr_request = curr_recsources
    curr_limit = (cpu_curr_limit, memory_curr_limit)
    curr_request = (cpu_curr_request, memory_curr_request)
    return curr_request, curr_limit

def add_to_update_list(update_list,workload,request_recommendations,limit_recommendations):
    cpu_request_recommendation, mem_request_recommendation = request_recommendations
    cpu_limit_recommendation, mem_limit_recommendation = limit_recommendations
    update_list[0].append(workload)
    update_list[1].append(cpu_request_recommendation)
    update_list[2].append(cpu_limit_recommendation)
    update_list[3].append(mem_request_recommendation)
    update_list[4].append(mem_limit_recommendation)

def add_to_insert_list(insert_list,workload,request_recommendations,limit_recommendations):
    cpu_request_recommendation, mem_request_recommendation = request_recommendations
    cpu_limit_recommendation, mem_limit_recommendation = limit_recommendations
    workload_name, namespace = workload
    insert_list.append((workload_name, cpu_request_recommendation,cpu_limit_recommendation,
                        mem_request_recommendation, mem_limit_recommendation,namespace))
def check_for_updates():
    """
    Check if there is a need for any resources update for each workload.
    If there is a need the function will upload it to the update table.
    """
    db_host, db_user, db_pass, db_name = PDB_ARGS
    pdb = PDB(db_host, db_user, db_pass, db_name)
    update_start = time.time()
    try:
        logging.info("Fetching all workloads form DB")
        # getting all the trained and enabled workloads in the form of (workload_name, namespace)
        all_workloads = pdb.Workload.get_enabled_workloads(trained=True, enabled=True)
        # getting all the workloads in Update table in the form of (workload_name, namespace)
        logging.info("Fetching all workloads that need resource's update from DB")
        workloads_in_table = pdb.Updates.get_workloads_to_update()
        # current request and limit for all workloads
        # where the key : (workload_name,namespace) and value:  resources tuple in size 4
        logging.info("Fetching all workloads current request and limit form DB")
        workloads_resources_pair = get_workloads_resources(all_workloads, pdb)
        # max predictions from the last 50 min for all workloads in a dictionary form
        logging.info("Fetching predictions for all workloads from DB")
        workload_predictions = get_workloads_preds(all_workloads,pdb)
        # initialize list to insert or update in the update list
        insert_list = []
        update_list = [[],[],[],[],[],[]]
        # going over all the workloads to check who needs a resource update
        logging.info("Checking what workload need an update")
        for workload in all_workloads:
            cpu_prediction, memory_prediction = workload_predictions[tuple(workload)]
            request_recommendations, limit_recommendations = get_recommendation_for_workload(cpu_prediction,memory_prediction)
            curr_request, curr_limit = get_curr_resources_for_workload(workload, workloads_resources_pair)
            if check_recommendations(request_recommendations,curr_request):
                if workloads_in_table is not None and workload in workloads_in_table:
                    logging.info(f"workload: {workload} needs resource change but already in table, adding it to update list list")
                    add_to_update_list(update_list, workload, request_recommendations, limit_recommendations)
                else:
                    logging.info(f"workload: {workload} needs resource change, adding it to insert list list")
                    add_to_insert_list(insert_list, workload, request_recommendations, limit_recommendations)
        logging.info(f"Update list: {update_list}\n insert list: {insert_list}")
        if len(update_list) > 0:
            pdb.Updates.update(update_list[0],update_list[1],update_list[2],update_list[3],update_list[4])
        else:
            logging.info("No workloads needs be updated in the Update table")
        if len(insert_list) > 0:
            attributes = ('workload_name', 'cpu_request', 'cpu_limit', 'memory_request', 'memory_limit','namespace')
            pdb.Updates.insert(attributes=attributes, values=insert_list)
        else:
            logging.info("No workloads needs be added to the Update table")

        close_connection(pdb.connection)

    except Exception as err:
        logging.error(f"Check for update task failed: %s", err)
        logging.error(traceback.format_exc())
        close_connection(pdb.connection)

    update_end = time.time() - update_start
    if update_end > 0.5 * 60:
        try:
            logging.warning("Update check takes too long, clearing data")
            pdb.Predictions.clear_data(all=True)
        except Exception as err:
            logging.error(f"Clearing data for {id} failed: %s", err)
            logging.error(traceback.format_exc())


