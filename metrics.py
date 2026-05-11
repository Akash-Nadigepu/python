import requests
import json

# List of Kafka instances (JMX exporter endpoints)
METRICS_URLS = [
    "http://localhost:7071/metrics",
    "http://localhost:7072/metrics",
    "http://localhost:7073/metrics"
]

REQUIRED_METRICS = {
    "cpu_load": "java_lang_OperatingSystem_CpuLoad",
    "request_handler_idle": "kafka_server_KafkaRequestHandlerPool_FiveMinuteRate",
    "failed_fetch_requests": "kafka_server_BrokerTopicMetrics_MeanRate{name=\"FailedFetchRequestsPerSec\",}",
    "failed_produce_requests": "kafka_server_BrokerTopicMetrics_MeanRate{name=\"FailedProduceRequestsPerSec\",}",
    "kafka_controller_active_controller": "kafka_controller_KafkaController_ActiveControllerCount",
    "kafka_controller_offline_partitions": "kafka_controller_KafkaController_OfflinePartitionsCount",
    "kafka_server_under_replicated_partitions": "kafka_server_ReplicaManager_UnderReplicatedPartitions",
    "kafka_server_isr_shrinks_total": "kafka_server_ReplicaManager_IsrShrinksPerSec",
    "kafka_server_isr_expands_total": "kafka_server_ReplicaManager_IsrExpandsPerSec",
    "kafka_server_messages_in_per_sec": "kafka_server_BrokerTopicMetrics_MeanRate{name=\"MessagesInPerSec\",}",
    "kafka_server_bytes_in_per_sec": "kafka_server_BrokerTopicMetrics_MeanRate{name=\"BytesInPerSec\",}",
    "kafka_server_bytes_out_per_sec": "kafka_server_BrokerTopicMetrics_MeanRate{name=\"BytesOutPerSec\",}",
    "kafka_network_requests_total": "kafka_network_RequestMetrics_Count",
    "kafka_network_request_time_ms": "kafka_network_RequestMetrics_TotalTimeMs",
    "kafka_consumer_lag": "kafka_consumer_fetch_manager_metrics_records_lag_max",
    "kafka_log_size_bytes": "kafka_log_Log_Value"
}


def fetch_metrics(url):
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        raise Exception(f"{url} failed with HTTP {response.status_code}")
    return response.text.splitlines()


def parse_metrics(metrics_lines):
    extracted_metrics = {k: [] for k in REQUIRED_METRICS}

    for line in metrics_lines:
        line = line.strip()

        if line.startswith("#") or line == "":
            continue

        for key, metric_name in REQUIRED_METRICS.items():
            if line.startswith(metric_name):
                try:
                    value = float(line.split()[-1])
                    extracted_metrics[key].append({
                        "metric": line.split()[0],
                        "value": value
                    })
                except:
                    pass

    return extracted_metrics


def validate_health(metrics):
    health_status = {
        "broker_healthy": True,
        "issues": []
    }

    for item in metrics.get("cpu_load", []):
        if item["value"] > 0.80:
            health_status["broker_healthy"] = False
            health_status["issues"].append(f"High CPU: {item['value']}")

    for item in metrics.get("request_handler_idle", []):
        if item["value"] < 0.20:
            health_status["broker_healthy"] = False
            health_status["issues"].append(f"Low request handler idle: {item['value']}")

    for item in metrics.get("kafka_controller_offline_partitions", []):
        if item["value"] > 0:
            health_status["broker_healthy"] = False
            health_status["issues"].append(f"Offline partitions: {item['value']}")

    for item in metrics.get("kafka_server_under_replicated_partitions", []):
        if item["value"] > 0:
            health_status["broker_healthy"] = False
            health_status["issues"].append(f"Under replicated partitions: {item['value']}")

    return health_status


def main():
    cluster_result = {
        "cluster_healthy": True,
        "instances": []
    }

    for url in METRICS_URLS:

        try:
            metrics_lines = fetch_metrics(url)

            parsed_metrics = parse_metrics(metrics_lines)

            health_status = validate_health(parsed_metrics)

            instance_result = {
                "metrics_url": url,
                "metrics": parsed_metrics,
                "health_status": health_status
            }

            if not health_status["broker_healthy"]:
                cluster_result["cluster_healthy"] = False

            cluster_result["instances"].append(instance_result)

        except Exception as e:
            cluster_result["cluster_healthy"] = False

            cluster_result["instances"].append({
                "metrics_url": url,
                "error": str(e),
                "broker_healthy": False
            })

    print(json.dumps(cluster_result, indent=4))


if __name__ == "__main__":
    main()
