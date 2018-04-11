#!/usr/bin/env python
import psutil
import json
import sys
from kafka import KafkaConsumer
import NetworkModel
import MultiLevelNetworkModel
import MultiLevelNetworkAnomaly
import datetime

model1 = lambda: None
model2 = lambda: None
model3 = lambda: None

def runModel(jsonData):
	global model1
	global model2
	global model3

	print("RunMethod" + str(jsonData))
	cpuMetric = float(json.loads(jsonData)['cpu'])
	memMetric = float(json.loads(jsonData)['mem'])
	
	start = datetime.datetime.now()
	actualVal, predictions, errorVal, anomalyScore = NetworkModel.runNetwork(model1.network, model1.dataSource, cpuMetric, False)
	end = datetime.datetime.now()
	elapsed = end - start
	model1.outputFile.write(actualVal + "|" + str(predictions) + "|" + errorVal + "|" + str(anomalyScore) + "|" +elapsed.microseconds +"\n")
	model1.outputFile.flush()
	
	start = datetime.datetime.now()
	actualVal, predictions, errorVal, anomalyScore = MultiLevelNetworkModel.runNetwork(model2.network, model2.dataSource, cpuMetric, False)
	end = datetime.datetime.now()
	elapsed = end - start
	model2.outputFile.write(actualVal + "|" + str(predictions) + "|" + errorVal + "|" + str(anomalyScore) + "|" + elapsed.microseconds +"\n")
	model2.outputFile.flush()
	
	start = datetime.datetime.now()
	actualVal, anomalyScore = MultiLevelNetworkAnomaly.runNetwork(model3.network, model3.dataSource, cpuMetric, memMetric, False)
	end = datetime.datetime.now()
	elapsed = end - start
	model3.outputFile.write(actualVal + "|" + str(anomalyScore) + "|" + elapsed.microseconds +"\n")
	model3.outputFile.flush()
	
def initModels():
	global model1
	model1.dataSource, model1.network = NetworkModel.BuildNetwork()
	model1.outputFile = open("model1.txt","w+")
	model1.outputFile.write("actualVal|predictions|avgError|anomalyScore|microseconds")
	model1.outputFile.flush()
	
	global model2
	model2.dataSource, model2.network = MultiLevelNetworkModel.BuildNetwork()
	model2.outputFile = open("model2.txt","w+")
	model2.outputFile.write("actualVal|predictions|avgError|anomalyScore|microseconds")
	model2.outputFile.flush()
	
	global model3
	model3.dataSource, model3.network = MultiLevelNetworkAnomaly.BuildNetwork()
	model3.outputFile = open("model3.txt","w+")
	model3.outputFile.write("actualVal|anomalyScore|microseconds")
	model3.outputFile.flush()
	
def main():
	var_bootstrap_servers=sys.argv[1]+':9092'
	initModels()
	
	consumer = KafkaConsumer('HTMTrainingData', group_id="ModelConsumerGp", bootstrap_servers=var_bootstrap_servers)
	
	for msg in consumer:
		runModel(msg.value)
    
if __name__ == "__main__":
    main()
