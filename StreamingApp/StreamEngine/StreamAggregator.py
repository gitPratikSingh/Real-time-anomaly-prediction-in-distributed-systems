import kafka
from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka.errors import KafkaError
import threading


def response_time_aggregator(bootstrap_servers, interval_length):
    end_of_time = None
    msg_counter = 0
    total_time = 0
    consumer_topic = 'responsetime'
    producer_topic = 'ag-responsetime'

    while True:
        try:
            producer = KafkaProducer(bootstrap_servers=[bootstrap_servers])
            consumer = KafkaConsumer(consumer_topic,
                                     auto_offset_reset='earliest',
                                     bootstrap_servers=[bootstrap_servers])

            while True:
                for message in consumer:
                    try:
                        msg = message.value.split(',')
                        response_time = int(msg[0])
                        epoch_time = int(msg[1])
                        if not end_of_time:
                            end_of_time = ((epoch_time/10) * 10) + interval_length

                    except ValueError as err:
                        print err
                        continue

                    if end_of_time < epoch_time:
                        # Process messages in this interval and produce
                        total_time /= msg_counter
                        future = producer.send(producer_topic, str(",".join([str(end_of_time), str(total_time)])))
                        # Block for 'synchronous' sends
                        try:
                            future.get(timeout=10)
                        except KafkaError as err:
                            print err

                        # Initialize for next interval
                        msg_counter = 1
                        total_time = response_time
                        end_of_time = ((epoch_time/10) * 10) + interval_length
                    else:
                        msg_counter += 1
                        total_time += response_time
        except kafka.errors.NoBrokersAvailable:
            pass


def cpu_time_aggregator(bootstrap_servers, interval_length):
    end_of_time = None
    msg_counter = 0
    total_time = 0
    consumer_topic = 'cpu'
    producer_topic = 'ag-cpu'

    while True:
        try:
            producer = KafkaProducer(bootstrap_servers=[bootstrap_servers])
            consumer = KafkaConsumer(consumer_topic,
                                     auto_offset_reset='earliest',
                                     bootstrap_servers=[bootstrap_servers])

            while True:
                for message in consumer:
                    try:
                        msg = message.value.split(',')
                        epoch_time = int(msg[0])
                        cpu_time = int(msg[1])
                        if not end_of_time:
                            end_of_time = ((epoch_time / 10) * 10) + interval_length

                    except ValueError as err:
                        print err
                        continue

                    if end_of_time < epoch_time:
                        # Process messages in this interval and produce
                        total_time /= msg_counter
                        future = producer.send(producer_topic, str(",".join([str(end_of_time), str(total_time)])))
                        # Block for 'synchronous' sends
                        try:
                            future.get(timeout=10)
                        except KafkaError as err:
                            print err

                        # Initialize for next interval
                        msg_counter = 1
                        total_time = cpu_time
                        end_of_time = ((epoch_time / 10) * 10) + interval_length
                    else:
                        msg_counter += 1
                        total_time += cpu_time
        except kafka.errors.NoBrokersAvailable:
            pass

class FuncThread(threading.Thread):
    thread_number = 1

    def __init__(self, target, *args):
        self._target = target
        self._args = args
        threading.Thread.__init__(self)
        FuncThread.thread_number += 1

    def run(self):
        self._target(*self._args)


def main():
    interval_length = 10
    bootstrap_servers = '172.25.130.9:9092'
    cpu_time_aggregator(bootstrap_servers, interval_length)
    # response_time_aggregator(bootstrap_servers, interval_length)
    # t1 = FuncThread(cpu_time_aggregator, bootstrap_servers, interval_length)
    # t1.setDaemon(True)
    # t1.start()


if __name__ == "__main__":
    main()
