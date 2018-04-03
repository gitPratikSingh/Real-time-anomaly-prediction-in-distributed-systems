import psutil
import time
import kafka
from kafka import KafkaProducer
from kafka.errors import KafkaError


def main():
    producer_topic = 'cpu'
    bootstrap_servers = '172.25.130.9:9092'
    while True:
        try:
            last_epoch = str(int(time.time()))
            producer = KafkaProducer(bootstrap_servers=[bootstrap_servers])
            while True:
                epoch = str(int(time.time()))
                if last_epoch != epoch:
                    cpu = str(int(psutil.cpu_percent(interval=1)))
                    mem = str(int(psutil.virtual_memory().percent))
                    data = ",".join([epoch, cpu, mem])
                    last_epoch = epoch
                    future = producer.send(producer_topic, data)
                    # Block for 'synchronous' sends
                    try:
                        future.get(timeout=10)
                    except KafkaError as err:
                        print err
        except kafka.errors.NoBrokersAvailable:
            pass


if __name__ == "__main__":
    main()
