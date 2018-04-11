import kafka
from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka.errors import KafkaError
import json


def insert(data, stats, response_time):
    produce = None
    if response_time:
        if response_time["timestamp"] > data["curr"]["timestamp"]:
            produce = data["prev"].copy()
            if produce["count"]:
                produce["average"] = produce["response_time_total"] / produce["count"]
            else:
                produce["average"] = 0
            data["prev"] = data["curr"].copy()
            data["curr"] = {}
            data["curr"]["timestamp"] = response_time["timestamp"]
            data["curr"]["response_time_total"] = response_time["response_time"]
            data["curr"]["count"] = 1
            return produce
        elif response_time["timestamp"] == data["curr"]["timestamp"]:
            data["curr"]["response_time_total"] += response_time["response_time"]
            data["curr"]["count"] += 1
            return produce
        elif response_time["timestamp"] == data["prev"]["timestamp"]:
            data["prev"]["response_time_total"] += response_time["response_time"]
            data["prev"]["count"] += 1
        else:
            return produce

    elif stats:
        if stats["timestamp"] > data["curr"]["timestamp"]:
            produce = data["prev"].copy()
            if produce["count"]:
                produce["average"] = produce["response_time_total"] / produce["count"]
            else:
                produce["average"] = 0
            data["prev"] = data["curr"].copy()
            data["curr"] = {}
            data["curr"]["timestamp"] = stats["timestamp"]
            data["curr"]["cpu"] = stats["cpu"]
            data["curr"]["mem"] = stats["mem"]
            data["curr"]["count"] = 0
            return produce
        else:
            return produce


def response_time_aggregator(bootstrap_servers):
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
                    "response_time_total": 0,
                    "average": 0,
                },
                "prev": {
                    "timestamp": 0,
                    "cpu": 0,
                    "mem": 0,
                    "count": 0,
                    "response_time_total": 0,
                    "average": 0,
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
                msg = stats_consumer.next()
                message = msg.value.split(',')
                produce = insert(data=data,
                                 stats={"timestamp": int(message[0]), "cpu": int(message[1]), "mem": int(message[2])},
                                 response_time=None)
                if produce:
                    print "stats produced\n"
                    aggregate_producer.send(aggregate_topic, json.dumps(produce))  # not a synchronous send

                produce = None
                c = 0
                while not produce:
                    c += 1
                    msg = response_time_consumer.next()
                    message = msg.value.split(',')
                    produce = insert(data=data,
                                     response_time={"timestamp": int(message[1]), "response_time": int(message[0])},
                                     stats=None)
                print "response time produced {}\n".format(c)
                aggregate_producer.send(aggregate_topic, json.dumps(produce))  # not a synchronous send

        except kafka.errors.NoBrokersAvailable:
            pass


def main():
    bootstrap_servers = '172.25.130.9:9092'
    response_time_aggregator(bootstrap_servers)


if __name__ == "__main__":
    main()
