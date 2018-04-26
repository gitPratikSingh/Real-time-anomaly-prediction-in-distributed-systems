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
                    print "*** VIOLATION: {} ***".format(response_time)
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
                data[timestamp]["violations"] = 0
            data[timestamp]["cpu"] = cpu
            data[timestamp]["mem"] = mem

    return timestamps


def response_time_aggregator():
    response_time_topic = 'responsetime'
    stats_topic = 'stats'
    aggregate_topic = 'aggregate'
    delay = 6
    with open("aggregate", "a+") as f:
        while True:
            try:
                while True:
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

                        # Consume responses for until the delay
                        while len(timestamps) < delay:
                            msg = response_time_consumer.next()
                            message = msg.value.split(',')
                            timestamps = insert_data(timestamp=int(message[1]),
                                                     response_time=int(message[0]),
                                                     cpu=None,
                                                     mem=None)
                        if len(timestamps) > delay - 1:

                            timestamp = min(timestamps)
                            aggregate = data.pop(timestamp)
                            aggregate["timestamp"] = timestamp
                            if not aggregate['cpu']:
                                raise KeyError
                            if len(aggregate.keys()) == 7:  # Produce clean data
                                try:
                                    aggregate["mean"] = aggregate['summation'] / aggregate['count']
                                except ZeroDivisionError:
                                    aggregate["mean"] = 0
                                jsondump = json.dumps(aggregate)
                                aggregate_producer.send(aggregate_topic, jsondump)
                                f.writelines(jsondump + "\n")
                                print(jsondump + "\n")

            except kafka.errors.NoBrokersAvailable:
                pass
            except KeyError:
                pass


parser = argparse.ArgumentParser()
parser.add_argument("-i", "--ip", help="IP/Hostname of Kafka instance", default='172.25.130.9', required=False)
parser.add_argument("-p", "--port", help="Port number of Kafka", default='9092', required=False)
parser.add_argument("-v", "--violation", help="SLO violation limit (milliseconds)", default=70, type=int, required=False)
args = parser.parse_args()
violation = args.violation
data = {}
bootstrap_servers = ":".join([args.ip, args.port])
response_time_aggregator()
