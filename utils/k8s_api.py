from typing import Tuple, Dict
from pylon.core.tools import log
from kubernetes.client import V1Container, CoreV1Api, V1ResourceQuotaList, Configuration, \
    ApiClient


def _normalize_cpu(cpu: str) -> float:
    """
    Normalize a CPU value expressed as a string to a floating point value in millicores.

    :param cpu: The CPU value to normalize, expressed as a string with a unit suffix.
                Supported units are: m (millicores), mu (microcores), u (microcores),
                n (nanocores).
    :return: The normalized CPU value in millicores.

    :raises ValueError: If the provided CPU unit is not recognized.
    """
    cpu = str(cpu)
    if cpu[-1:].isdigit():
        return float(cpu) * 1000
    if cpu[-1:] == "m":
        return float(cpu[:-1])
    elif cpu[-2:] == "mu":
        return float(cpu[:-2]) / 1000
    elif cpu[-1:] == "u":
        return float(cpu[:-1]) / 1000
    elif cpu[-2:] == "n":
        return float(cpu[:-2]) / 1000000
    raise ValueError(f"Invalid CPU unit {cpu[-2:]}")


def _normalize_memory(memory: str) -> float:
    """
    Normalize a memory value expressed as a string to a floating point value in MiB.

    :param memory: The memory value to normalize, expressed as a string with a unit suffix.
                   Supported units are: Ki (kibibytes), K (kilobytes), Mi (mebibytes),
                   M (megabytes), Gi (gibibytes), G (gigabytes).
    :return: The normalized memory value in MiB.
    :raises ValueError: If the provided memory unit is not recognized.
    """
    memory = str(memory)
    if memory[-1:].isdigit():
        return float(memory)
    if memory.endswith("Ki"):
        return float(memory[:-2]) / 1024
    if memory.endswith("K"):
        return float(memory[:-1]) / 1024
    if memory.endswith("Mi"):
        return float(memory[:-2])
    if memory.endswith("M"):
        return float(memory[:-1])
    if memory.endswith("Gi"):
        return float(memory[:-2]) * 1024
    if memory.endswith("G"):
        return float(memory[:-1]) * 1024
    raise ValueError(f"Invalid memory unit {memory[-2:]}")


def get_cluster_capacity(v1: CoreV1Api, namespace: str) -> Dict[str, float]:
    """
    Retrieve the cluster capacity for a given namespace in a Kubernetes cluster.

    :param v1: a `CoreV1Api` object for interacting with the Kubernetes API.
    :param namespace: the name of the namespace.

    :return: a dictionary with keys 'cpu' and 'memory' representing the maximum capacity
    for CPU and memory in the namespace, respectively.
    """
    quotas = v1.list_namespaced_resource_quota(namespace=namespace)

    cluster_cpu_capacity, cluster_memory_capacity, cluster_pods_capacity = \
        get_max_cluster_capacity(v1)
    namespaces = v1.list_namespace()
    cluster_memory_usage = 0.0
    cluster_cpu_usage = 0.0
    cluster_pods_usage = 0
    for namespace in namespaces.items:
        namespace_cpu_usage, namespace_memory_usage, namespace_pods_usage = \
            get_namespace_resource_usage(v1, namespace.metadata.name)

        cluster_memory_usage += namespace_memory_usage
        cluster_cpu_usage += namespace_cpu_usage
        cluster_pods_usage += namespace_pods_usage

    log.info(f"{cluster_memory_capacity=} {cluster_memory_usage=}")
    cluster_memory_free = cluster_memory_capacity - cluster_memory_usage - 300.0
    cluster_cpu_free = cluster_cpu_capacity - cluster_cpu_usage
    cluster_pods_usage = cluster_pods_capacity - cluster_pods_usage
    max_capacity_node = {
        'cpu': cluster_cpu_free, 'memory': cluster_memory_free, "pods": cluster_pods_usage
    }

    if quotas.items:
        max_capacity_quota = get_from_quota(quotas)
        max_capacity = {
            "cpu": min(max_capacity_quota["cpu"], max_capacity_node["cpu"]),
            "memory": min(max_capacity_quota["memory"], max_capacity_node["memory"]),
            "pods": min(max_capacity_quota["pods"], max_capacity_node["pods"])
        }
    else:
        max_capacity = max_capacity_node

    return max_capacity


def get_namespace_resource_usage(v1: CoreV1Api, namespace: str) -> Tuple[float, float, int]:
    """
    Calculate the total resource usage (CPU and memory) of all pods in a namespace.

    :param namespace: The namespace to calculate resource usage for.
    :return: A tuple containing the total CPU usage and total memory usage of all pods in the namespace,
             in that order.
    """

    namespace_memory_usage = 0
    namespace_cpu_usage = 0
    namespace_pods_usage = 0
    pods = v1.list_namespaced_pod(namespace)
    for pod in pods.items:
        pod_memory_usage = 0
        pod_cpu_usage = 0
        namespace_pods_usage += 1
        for container in pod.spec.containers:
            container_cpu_usage, container_memory_usage = get_container_resource_usage(
                container)

            pod_memory_usage += container_memory_usage
            pod_cpu_usage += container_cpu_usage

        namespace_cpu_usage += pod_cpu_usage
        namespace_memory_usage += pod_memory_usage
    return namespace_cpu_usage, namespace_memory_usage, namespace_pods_usage


def get_container_resource_usage(container: V1Container) -> Tuple[float, float]:
    """
    Calculate the resource usage (CPU and memory) of a container.

    The resource usage is calculated as the maximum
    of the container's resource requests and limits.

    :param container: The container to calculate resource usage for.

    :return: A tuple containing the CPU usage and memory usage of the container, in that order.
    """
    resources = container.resources
    if resources.limits:
        container_cpu_limit = resources.limits.get('cpu', "0")
        container_memory_limit = resources.limits.get('memory', "0")
        container_cpu_limit = _normalize_cpu(container_cpu_limit)
        container_memory_limit = _normalize_memory(container_memory_limit)
    else:
        container_cpu_limit, container_memory_limit = 0, 0
    if resources.requests:
        container_cpu_request = resources.requests.get('cpu', "0")
        container_memory_request = resources.requests.get('memory', "0")
        container_cpu_request = _normalize_cpu(container_cpu_request)
        container_memory_request = _normalize_memory(container_memory_request)
    else:
        container_cpu_request, container_memory_request = 0, 0
    container_memory_usage = max(container_memory_request,
                                 container_memory_limit)
    container_cpu_usage = max(container_cpu_request, container_cpu_limit)
    return container_cpu_usage, container_memory_usage


def get_max_cluster_capacity(v1: CoreV1Api) -> Tuple[float, float, int]:
    """
    Calculate the maximum capacity for CPU and memory in a namespace.

    The maximum capacity is calculated as the maximum capacity of all nodes in the cluster.

    :return: a tuple containing the maximum CPU capacity and maximum memory
    capacity of the namespace, in that order.
    """
    max_capacity = {'cpu': "0m", 'memory': "0Mi", "pods": 0}
    nodes = v1.list_node()
    if not nodes.items:
        raise ValueError("Can't calculate capacity for auto scaling cluster")
    for node in nodes.items:
        node_capacity = node.status.capacity
        max_capacity['cpu'] = max(_normalize_cpu(max_capacity['cpu']),
                                  _normalize_cpu(node_capacity['cpu']))
        max_capacity['memory'] = max(_normalize_memory(max_capacity['memory']),
                                     _normalize_memory(node_capacity['memory']))
        max_capacity["pods"] = max(int(node_capacity["pods"]), max_capacity["pods"])

    cluster_memory_capacity = max_capacity["memory"]
    cluster_cpu_capacity = max_capacity["cpu"]
    cluster_pods_capacity = max_capacity["pods"]
    return cluster_cpu_capacity, cluster_memory_capacity, cluster_pods_capacity


def get_from_quota(quotas: V1ResourceQuotaList) -> Dict[str, float]:
    """
    Calculate the maximum capacity for CPU and memory in a namespace based on resource quotas.

    The maximum capacity is calculated as the maximum
    available capacity for each resource in all quotas.

    :param quotas: The resource quotas to calculate the maximum capacity from.

    :return: A dictionary containing the maximum CPU capacity
          and maximum memory capacity of the namespace,
          with keys 'cpu' and 'memory', respectively.
    """

    max_capacity = {'cpu': "0m", 'memory': "0Mi", "pods": 0}
    for quota in quotas.items:
        quota_limit = quota.status.hard
        quota_used = quota.status.used
        quota_limit_cpu = min(
            _normalize_cpu(quota_limit.get("cpu", "0")),
            _normalize_cpu(quota_limit.get("limits.cpu", "0")),
            _normalize_cpu(quota_limit.get("requests.cpu", "0")),
        )
        quota_limit_memory = min(
            _normalize_memory(quota_limit.get("memory", "0")),
            _normalize_memory(quota_limit.get("limits.memory", "0")),
            _normalize_memory(quota_limit.get("requests.memory", "0")),
        )
        quota_usage_cpu = max(
            _normalize_cpu(quota_used.get("cpu", "0")),
            _normalize_cpu(quota_used.get("limits.cpu", "0")),
            _normalize_cpu(quota_used.get("requests.cpu", "0")),
        )
        quota_usage_memory = max(
            _normalize_memory(quota_used.get("memory", "0")),
            _normalize_memory(quota_used.get("limits.memory", "0")),
            _normalize_memory(quota_used.get("requests.memory", "0")),
        )
        free_cpu_in_quota = quota_limit_cpu - quota_usage_cpu
        free_space_in_quota = quota_limit_memory - quota_usage_memory
        free_pods_in_quota = int(quota_limit["pods"]) - int(quota_used["pods"])

        max_capacity['cpu'] = max(_normalize_cpu(max_capacity['cpu']),
                                  free_cpu_in_quota)
        max_capacity['memory'] = max(_normalize_memory(max_capacity['memory']),
                                     free_space_in_quota)
        max_capacity["pods"] = max(max_capacity["pods"], free_pods_in_quota)

    return max_capacity


def get_core_api(token: str, hostname: str, secure_connection: bool = False) -> CoreV1Api:
    """
    Create a `CoreV1Api` object for interacting with the Kubernetes API.

    :param token: the token to authenticate with the Kubernetes API.
    :param hostname: the hostname of the Kubernetes API.
    :param secure_connection: whether to verify ssl certificate when communicating
    with the Kubernetes API. Defaults to False.

    :return: a `CoreV1Api` object for interacting with the Kubernetes API.
    """
    configuration = Configuration()

    configuration.api_key_prefix['authorization'] = 'Bearer'
    configuration.api_key['authorization'] = token
    configuration.host = hostname.rstrip('/')
    configuration.verify_ssl = secure_connection

    core_api = CoreV1Api(ApiClient(configuration))
    return core_api
