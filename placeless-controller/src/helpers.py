import json
from datetime import datetime
import re

import logging
from api import WorkloadActions, ResourcesAction

DEFAULT_CONTAINER_RESOURCES_MAP = {"limits": {"cpu": "0m", "memory": "0Mi"}, "requests": {"cpu": "0m", "memory": "0Mi"}}
UNIT_REGEX = re.compile(r'(\d+)([a-zA-Z]+)')
UNIT_MAP_FUNCTION = {'cpu': {'m': lambda a: a * 1000000000},
                     'memory': {'Mi': lambda a: a * (1024 ** 2),
                                'Gi': lambda a: a * (1024 ** 3),
                                'Ki': lambda a: a * 1024}}


def _return_resource_value(type, str_value):
    value, unit = UNIT_REGEX.search(str_value).groups()
    return UNIT_MAP_FUNCTION[type][unit](int(value))


def _check_recommendations(recommendations, current_resources):
    cpu_request, memory_request = current_resources['cpu'], current_resources['memory']
    recommended_cpu_request = recommendations['resources']['request']['cpu']
    recommended_memory_request = recommendations['resources']['request']['memory']
    check_cpu = lambda r1, r0: (abs(r1 - r0) / r0) * 100 > 5 or abs(r1 - r0) > 1 * 10 ** 9
    check_memory = lambda r1, r0: (abs(r1 - r0) / r0) * 100 > 5 or abs(r1 - r0) > 100 * 10 ** 6
    return check_cpu(recommended_cpu_request, cpu_request) or check_memory(recommended_memory_request, memory_request)


def get_container_index(containers_list, container_name):
    if isinstance(containers_list[0], dict):
        return [ind for ind in range(containers_list.__len__()) if containers_list[ind]['name'] == container_name][0]
    return [ind for ind in range(containers_list.__len__()) if containers_list[ind].name == container_name][0]


def get_container_name(body: dict):
    containers_list = body['spec']['template']['spec']['containers']
    if len(containers_list) == 1:
            index = 0
            container_in_first_index: dict = containers_list[0]
            name = container_in_first_index['name']
            return name, index
    try:
        name = body['metadata']['labels']['placeless/container_name']
        index = get_container_index(containers_list, name)
        return name, index
    except KeyError:
        return None, None


def register_workload_in_pdb(spec, body):
    current_time = datetime.now()
    container_name, container_index = get_container_name(body)
    if container_index is None:
        logging.info(f"Ignoring deployment {body['metadata']['name']} has multiple containers.")
        return
    logging.info(f"deployment name {body['metadata']['name']} associate with container {container_name} index {container_index}")
    container_current = spec['template']['spec']['containers'][container_index]
    container_current_resources = container_current['resources']
    container_current_resources_limits = container_current_resources.get("limits", {})
    container_current_resources_requests = container_current_resources.get("requests", {})
    workload_dict = {"workload_name": body['metadata']['name'],
                     "workload_namespace": body['metadata']['namespace'],
                     "creation_TS": current_time.timestamp(),
                     "creation_Date": current_time,
                     "CPU_limit": container_current_resources_limits.get("cpu", "0m"),
                     "memory_limit": container_current_resources_limits.get("memory", "0Mi"),
                     "CPU_request": container_current_resources_requests.get("cpu", "0m"),
                     "memory_request": container_current_resources_requests.get("memory", "0Mi"),
                     "AWS_FT": "single"}
    workload_action = WorkloadActions()
    workload_action.register_workload(args=workload_dict)


def is_workload_exist_in_placeless(body) -> bool:
    json_body = {'workload_name': body['metadata']['name'], "workload_namespace": body['metadata']['namespace']}
    workload_action = WorkloadActions()
    assert workload_action.is_exist(args=json_body) == True


def _set_deployment_resources(v1, kube_client, workload, details):
    deploy = None
    try:
        deploy = v1.read_namespaced_deployment(name=workload, namespace=details['namespace'])
    except kube_client.exceptions.ApiException:
        logging.error(f"{workload} exist in placless but not in cluster")
        return

    container_index = get_container_index(deploy.spec.template.spec.containers,
                                          deploy.metadata.labels['placeless/container_name'])
    deploy.spec.template.spec.containers[container_index].resources = details['resources']
    try:
        workload_handler = WorkloadActions()
        v1.patch_namespaced_deployment(
            name=workload, namespace=details['namespace'], body=deploy
        )
        logging.info(f"update {workload} - resource in k8s")
        try:
            args = {'workload_name': workload, 'workload_namespace': details['namespace'],
                    'resources': details['resources']}
            workload_handler.delete(args=args)
            workload_handler.set_resources(workload, details['namespace'], details['resources'])
            logging.info(f"successfully set new resources to {workload}")
        except Exception as err:
            logging.error(
                f"_set_deployment_resources | something went wrong while try to update placeless DB err - {err}")
    except Exception as err:
        logging.error(f"_set_deployment_resources(v1, kube_client, workload, details) "
                      f"- something went wrong with setting resource value for {workload}\n msg - {err}")


def update_workload_monitored_by_placeless(kube_client):
    logging.info("update_workload_monitored_by_placeless")
    v1 = kube_client.AppsV1Api()
    v1.read_namespaced_deployment
    workload_dict = ResourcesAction().get_resources()
    for workload, details in workload_dict.items():
        _set_deployment_resources(v1, kube_client, workload, details)


def create_new_workload(body, spec, **_):
    try:
        logging.info(f"creating... {body['metadata']['name']}")
        register_workload_in_pdb(spec, body)
    except ValueError as err:
        logging.error(err)