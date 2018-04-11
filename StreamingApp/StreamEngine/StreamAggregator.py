import kafka
from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
import argparse


def insert(data, stat, response):
    produce = None
    if response:
        if response["timestamp"] > data["curr"]["timestamp"]:
            produce = data["prev"].copy()
            if produce["count"]:
                produce["average"] = produce["summation"] / produce["count"]
            else:
                produce["average"] = 0
            data["prev"] = data["curr"].copy()
            data["curr"] = {}
            data["curr"]["timestamp"] = response["timestamp"]
            data["curr"]["summation"] = response["response_time"]
            data["curr"]["count"] = 1
            data["curr"]["max"] = response["response_time"]
            if response["response_time"] >= violation:
                data["curr"]["violations"] = 1
            else:
                data["curr"]["violations"] = 0
            return produce
        elif response["timestamp"] == data["curr"]["timestamp"]:
            data["curr"]["summation"] += response["response_time"]
            data["curr"]["count"] += 1
            if response["response_time"] >= violation:
                data["curr"]["violations"] += 1
            if data["curr"]["max"] < response["response_time"]:
                data["curr"]["max"] = response["response_time"]
            return produce
        elif response["timestamp"] == data["prev"]["timestamp"]:
            data["prev"]["summation"] += response["response_time"]
            data["prev"]["count"] += 1
            if response["response_time"] >= violation:
                data["prev"]["violations"] += 1
            if data["prev"]["max"] < response["response_time"]:
                data["prev"]["max"] = response["response_time"]
        else:
            return produce

    elif stat:
        if stat["timestamp"] == data["curr"]["timestamp"]:
            data["curr"]["cpu"] = stat["cpu"]
            data["curr"]["mem"] = stat["mem"]
            return produce
        else:
            return produce


def response_time_aggregator():
    response_time_topic = 'responsetime'
    stats_topic = 'stats'
    aggregate_topic = 'aggregate'

    while True:
        try:
            data = {
                "curr": {
                    "timestamp": 0,
                    "cpu": 0,
                    "mem": 0,
                    "count": 0,
                    "summation": 0,
                    "average": 0,
                    "max": 0,
                    "violations": 0
                },
                "prev": {
                    "timestamp": 0,
                    "cpu": 0,
                    "mem": 0,
                    "count": 0,
                    "summation": 0,
                    "average": 0,
                    "max": 0,
                    "violations": 0
                }
            }

            aggregate_producer = KafkaProducer(bootstrap_servers=[bootstrap_servers])
            response_time_consumer = KafkaConsumer(response_time_topic,
                                                   auto_offset_reset='earliest',
                                                   # auto_offset_reset='latest',
                                                   bootstrap_servers=[bootstrap_servers])
            stats_consumer = KafkaConsumer(stats_topic,
                                           auto_offset_reset='earliest',
                                           # auto_offset_reset='latest',
                                           bootstrap_servers=[bootstrap_servers])

            while True:
                # Consume stats every second
                msg = stats_consumer.next()
                message = msg.value.split(',')
                produce = insert(data=data,
                                 stat={"timestamp": int(message[0]), "cpu": int(message[1]), "mem": int(message[2])},
                                 response=None)
                # if produce:
                #     aggregate_producer.send(aggregate_topic, json.dumps(produce))  # not a synchronous send

                # Consumer responses for the entire second
                produce = None
                while not produce:
                    msg = response_time_consumer.next()
                    message = msg.value.split(',')
                    produce = insert(data=data,
                                     response={"timestamp": int(message[1]), "response_time": int(message[0])},
                                     stat=None)
                aggregate_producer.send(aggregate_topic, json.dumps(produce))  # not a synchronous send

        except kafka.errors.NoBrokersAvailable:
            pass


parser = argparse.ArgumentParser()
parser.add_argument("-i", "--ip", help="IP/Hostname of Kafka instance", default='172.25.130.9', required=False)
parser.add_argument("-p", "--port", help="Port number of Kafka", default='9092', required=False)
parser.add_argument("-v", "--violation", help="SLO violation limit (milliseconds)", default=100, type=int, required=False)
args = parser.parse_args()
violation = args.violation
bootstrap_servers = ":".join([args.ip, args.port])
response_time_aggregator()
