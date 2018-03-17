#!/usr/bin/env python
import psutil
import json
import sys
from kafka import KafkaConsumer
from PlainModel import Model

class StreamProcessEngine():
    model = None
    
    @classmethod
    def runModel(cls, jsonData):
        print("RunMethod" + str(jsonData))
        StreamProcessEngine.model.run(str(jsonData))
        
def main():
    var_bootstrap_servers=sys.argv[1]+':9092'
    model = Model()
    StreamProcessEngine.model = model
    consumer = KafkaConsumer('cpu_metric', group_id="ConsumerGp", bootstrap_servers=var_bootstrap_servers)
    for msg in consumer:
        StreamProcessEngine.runModel(msg.value)
        
if __name__ == "__main__":
    main()
