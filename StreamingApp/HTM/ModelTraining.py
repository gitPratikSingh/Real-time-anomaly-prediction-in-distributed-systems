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

_FILE_PATH = "../../ML/TrainingData.txt"

def runModel(jsonData):
	global model1
	global model2
	global model3

	print("RunMethod" + str(jsonData))
	cpuMetric = json.loads(jsonData)['cpu']
	memMetric = json.loads(jsonData)['mem']
	nothing = ['None', 'null', None]
	
	if(cpuMetric in nothing or memMetric in nothing):
		return;
		
	cpuMetric = float(cpuMetric)
	memMetric = float(memMetric)
	
	start = datetime.datetime.now()
	actualVal, predictions, errorVal, anomalyScore = NetworkModel.runNetwork(model1.network, model1.dataSource, cpuMetric, False, False)
	end = datetime.datetime.now()
	elapsed = end - start
	model1.outputFile.write(str(actualVal) + "|" + str(predictions) + "|" + errorVal + "|" + str(anomalyScore) + "|" +str(elapsed.microseconds/1000) +"\n")
	model1.outputFile.flush()
	"""
	start = datetime.datetime.now()
	actualVal, predictions, errorVal, anomalyScore = MultiLevelNetworkModel.runNetwork(model2.network, model2.dataSource, cpuMetric, False)
	end = datetime.datetime.now()
	elapsed = end - start
	model2.outputFile.write(str(actualVal) + "|" + str(predictions) + "|" + errorVal + "|" + str(anomalyScore) + "|" + str(elapsed.microseconds/1000) +"\n")
	model2.outputFile.flush()
	
	start = datetime.datetime.now()
	actualVal, anomalyScore = MultiLevelNetworkAnomaly.runNetwork(model3.network, model3.dataSource, cpuMetric, memMetric, False)
	end = datetime.datetime.now()
	elapsed = end - start
	model3.outputFile.write(str(actualVal) + "|" + str(anomalyScore) + "|" + str(elapsed.microseconds/1000) +"\n")
	model3.outputFile.flush()
	"""
	
def initModels():
	global model1
	model1.dataSource, model1.network = NetworkModel.BuildNetwork()
	model1.outputFile = open("model1.txt","w+")
	model1.outputFile.write("actualVal|predictions|avgError|anomalyScore|time(ms)\n")
	model1.outputFile.flush()
	
	"""
	global model2
	model2.dataSource, model2.network = MultiLevelNetworkModel.BuildNetwork()
	model2.outputFile = open("model2.txt","w+")
	model2.outputFile.write("actualVal|predictions|avgError|anomalyScore|time(ms)\n")
	model2.outputFile.flush()
	
	global model3
	model3.dataSource, model3.network = MultiLevelNetworkAnomaly.BuildNetwork()
	model3.outputFile = open("model3.txt","w+")
	model3.outputFile.write("actualVal|anomalyScore|time(ms)\n")
	model3.outputFile.flush()
	"""
	
def main():
	var_bootstrap_servers='172.25.130.9'+':9092'
	start = datetime.datetime.now()
	
	initModels()
	
	if len(sys.argv)==1:
		consumer = KafkaConsumer('aggregate1', group_id="ModelConsumerGp", bootstrap_servers=var_bootstrap_servers)
		for msg in consumer:
			runModel(msg.value)
	else:
		with open(_FILE_PATH, 'r') as f:
			for line in f:
				runModel(line)
	
	end = datetime.datetime.now()
	print("Time taken to train a model\n")
	print (end-start)
	
if __name__ == "__main__":
    main()
