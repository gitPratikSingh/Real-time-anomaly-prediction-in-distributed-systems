import kafka
from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
import argparse


def insert_data(timestamp, cpu, mem, response_time):
    timestamps = data.keys()
    try:
        min_timestamp = min(timestamps)
    except ValueError:
        min_timestamp = 0
    if min_timestamp > timestamp:
        return timestamps
    else:
        if response_time:
            if timestamp in timestamps:
                try:
                    data[timestamp]["summation"] += response_time
                except KeyError:
                    data[timestamp]["summation"] = response_time
                try:
                    data[timestamp]["count"] += 1
                except KeyError:
                    data[timestamp]["count"] = 1
                if response_time >= violation:
                    try:
                        data[timestamp]["violations"] += 1
                    except KeyError:
                        data[timestamp]["violations"] = 1
                try:
                    if data[timestamp]["max"] < response_time:
                        data[timestamp]["max"] = response_time
                except KeyError:
                    data[timestamp]["max"] = response_time
            else:
                timestamps.append(timestamp)
                data[timestamp] = {}
                data[timestamp]["summation"] = response_time
                data[timestamp]["count"] = 1
                if response_time >= violation:
                    data[timestamp]["violations"] = 1
                else:
                    data[timestamp]["violations"] = 0
                data[timestamp]["max"] = response_time
        else:
            if timestamp not in timestamps:
                data[timestamp] = {}
                timestamps.append(timestamp)
            data[timestamp]["cpu"] = cpu
            data[timestamp]["mem"] = mem
    return timestamps


def response_time_aggregator():
    response_time_topic = 'responsetime'
    stats_topic = 'stats'
    aggregate_topic = 'aggregate'

    while True:
        try:
            aggregate_producer = KafkaProducer(bootstrap_servers=[bootstrap_servers])
            response_time_consumer = KafkaConsumer(response_time_topic,
                                                   # auto_offset_reset='earliest',
                                                   auto_offset_reset='latest',
                                                   bootstrap_servers=[bootstrap_servers])
            stats_consumer = KafkaConsumer(stats_topic,
                                           # auto_offset_reset='earliest',
                                           auto_offset_reset='latest',
                                           bootstrap_servers=[bootstrap_servers])

            while True:
                # Consume stats every second
                msg = stats_consumer.next()
                message = msg.value.split(',')
                timestamps = insert_data(timestamp=int(message[0]),
                                         cpu=int(message[1]),
                                         mem=int(message[2]),
                                         response_time=None)

                # Consume responses for until third moment arrives
                while len(timestamps) < 3:
                    msg = response_time_consumer.next()
                    message = msg.value.split(',')
                    timestamps = insert_data(timestamp=int(message[1]),
                                             response_time=int(message[0]),
                                             cpu=None,
                                             mem=None)
                if len(timestamps) > 2:
                    timestamp = min(timestamps)
                    aggregate = data.pop(timestamp)
                    aggregate["timestamp"] = timestamp
                    print aggregate
                    if len(aggregate.keys()) == 7:  # Produce clean data
                        try:
                            aggregate["mean"] = aggregate['summation'] / aggregate['count']
                        except ZeroDivisionError:
                            aggregate["mean"] = 0
                        aggregate_producer.send(aggregate_topic, json.dumps(aggregate))  # not a synchronous send

        except kafka.errors.NoBrokersAvailable:
            pass


parser = argparse.ArgumentParser()
parser.add_argument("-i", "--ip", help="IP/Hostname of Kafka instance", default='172.25.130.9', required=False)
parser.add_argument("-p", "--port", help="Port number of Kafka", default='9092', required=False)
parser.add_argument("-v", "--violation", help="SLO violation limit (milliseconds)", default=100, type=int, required=False)
args = parser.parse_args()
violation = args.violation
data = {}
bootstrap_servers = ":".join([args.ip, args.port])
response_time_aggregator()
