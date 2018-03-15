#!/usr/bin/env python
import threading, logging, time
from kafka import KafkaProducer

import psutil
import json

class Producer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.stop_event = threading.Event()
        
    def stop(self):
        self.stop_event.set()

    def run(self):
        producer = KafkaProducer(value_serializer=lambda v: json.dumps(v).encode('utf-8'), bootstrap_servers='ec2-18-219-238-85.us-east-2.compute.amazonaws.com:9092')

        while not self.stop_event.is_set():
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory().percent 
            producer.send('cpu_metric', {"cpu_metric": cpu, "mem_metric":mem})
            print("Data pushed: "+ str(cpu))
            time.sleep(2)

        producer.close()
        
def main():
    tasks = [
        Producer()    ]

    for t in tasks:
        t.start()

    time.sleep(1000)
    
    for task in tasks:
        task.stop()

    for task in tasks:
        task.join()
        
        
if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
        level=logging.INFO
        )
    main()
