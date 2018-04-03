from kafka import KafkaConsumer
import threading


def data_collector(bootstrap_servers, topic, csv_file):
    consumer = KafkaConsumer(topic,
                             auto_offset_reset='earliest',
                             bootstrap_servers=[bootstrap_servers])

    with open(csv_file, 'w') as f:
        for message in consumer:
            try:
                f.write(message.value + '\n')
            except ValueError as err:
                print err
                continue


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
    bootstrap_servers = '172.25.130.9:9092'
    t1 = FuncThread(data_collector, bootstrap_servers, 'ag-responsetime', 'responsetime.csv')
    t2 = FuncThread(data_collector, bootstrap_servers, 'ag-stats', 'stats.csv')
    t1.setDaemon(False)
    t1.setDaemon(False)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

if __name__ == "__main__":
    main()
