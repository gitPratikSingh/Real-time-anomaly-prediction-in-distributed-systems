#!/usr/bin/env python
import psutil
import json
import sys
from kafka import KafkaConsumer
import NetworkModel
import MultiLevelNetworkModel
import MultiLevelNetworkAnomaly
import datetime
import NetworkUtils
import time
from nupic.engine import Network

_RECORD_SENSOR = "sensorRegion"
_FILE_PATH = "../../ML/TrainingData.txt"

model1 = lambda: None
model2 = lambda: None
model3 = lambda: None

model1.tp = 0
model1.fp = 0
model1.tn = 0
model1.fn = 0

_SLO_CPU=20
_ANOMALY_SCORE=0.5
_MAX_LEAD_TIME = 50
_SLO_RESPONSE_TIME = 70
_CONFIDENCE_LEVEL = 0.15

predictionList = list()
rcount=0
def runModel(jsonData):
	global model1
	global model2
	global model3
	global predictionList
	global rcount
	
	cpuSLOViolationPredictions=0
	AnomalyScoreViolation=0
	
	cpuMetric = json.loads(jsonData)['cpu']
	memMetric = json.loads(jsonData)['mem']
	violation = json.loads(jsonData)['violations']
	avgresponse = json.loads(jsonData)['mean']
	
	nothing = ['None', 'null', None]
	if(cpuMetric in nothing or memMetric in nothing):
		return;
	
	cpuMetric = float(cpuMetric)
	memMetric = float(memMetric)
	violation = int(violation)
	avgresponse = int(avgresponse)
	if avgresponse >= _SLO_RESPONSE_TIME:
		violation = 1
	
	rcount += 1
	anomalywindow = list()
	
	
	#print("RunMethod" + str(jsonData))
	actualVal, predictions, errorVal, anomalyScore = NetworkModel.runNetwork(model1.network, model1.dataSource, cpuMetric, False, True)
	anomalywindow.append(anomalyScore)
	
	for prediction in predictions:
		x, y, z, anomalyScore = NetworkModel.runNetwork(model1.network, model1.dataSource, cpuMetric, True, True)
		anomalywindow.append(anomalyScore)
	
	for anomaly in anomalywindow
		if anomaly > _ANOMALY_SCORE
			AnomalyScoreViolation = AnomalyScoreViolation + 1
		
	"""
	actualVal, predictions, errorVal, anomalyScore = MultiLevelNetworkModel.runNetwork(model2.network, model2.dataSource, cpuMetric, True)
	if all(prediction < _SLO_CPU for prediction in predictions) == False:
		cpuSLOViolationPredictions=cpuSLOViolationPredictions+1
	
	if anomalyScore > _ANOMALY_SCORE:
		AnomalyScoreViolation = AnomalyScoreViolation + 1
	
	actualVal, anomalyScore = MultiLevelNetworkAnomaly.runNetwork(model3.network, model3.dataSource, cpuMetric, memMetric, True)
	if all(prediction < _SLO_CPU for prediction in predictions) == False:
		cpuSLOViolationPredictions=cpuSLOViolationPredictions+1
	
	if anomalyScore > _ANOMALY_SCORE:
		AnomalyScoreViolation = AnomalyScoreViolation + 1
	"""
	
	# Raise alarm only when this satisfy
	if float(AnomalyScoreViolation)/len(predictions) > _CONFIDENCE_LEVEL:
		raiseAlarm(1)
		anomaly = list()
		anomaly.append(-1)
		anomaly.append('A')
		anomaly.append(rcount)
		anomaly.append('TP')
		predictionList.append(anomaly)
	else:
		normal = list()
		normal.append(-1)
		normal.append('N')
		normal.append(rcount)
		normal.append('TN')
		predictionList.append(normal)
		timenow = int(time.time())
	
	if violation > 0:
		processpredictionList('A', rcount)
		timenow = int(time.time())
		print("SLO violation at "+str(timenow)+" for record number "+ str(rcount))
	else:
		processpredictionList('N', rcount)
	
	
def raiseAlarm(modelId):
	print("Alarm raised by - Model " +str(modelId) + " at "+ str(int(time.time())))
	
def processpredictionList(state, rcount):
	global predictionList
	
	for item in predictionList:
		if item[0] == -1: # unprocessed
			if state == 'A':
				if item[1] == 'N':
					if rcount - item[2] <= _MAX_LEAD_TIME:
						item[3] = 'FN'
						item[0] = 0
				else:
					if rcount - item[2] <= _MAX_LEAD_TIME:
						item[3] = 'TP'
						item[0] = 0
			else:
				if item[1] == 'A':
					if rcount - item[2] > _MAX_LEAD_TIME:
						item[3] = 'FP'
						item[0] = 0
				else:
					if rcount - item[2] > _MAX_LEAD_TIME:
						item[3] = 'TN'
						item[0] = 0
	
def getModelStats():
	global predictionList
	tp=0
	fp=0
	fn=0
	tn=0
	for item in predictionList:
		if item[3] == 'TP':
			tp += 1
		if item[3] == 'TN':
			tn += 1
		if item[3] == 'FP':
			fp += 1
		if item[3] == 'FN':
			fn += 1
	
	print("TP: "+str(tp) + "FP: "+str(fp) + "TN: "+str(tn) + "FN: "+str(fn))	
	print("Model accuracy" +str(float((tp + tn))/(tp + tn + fn + fp)))
	
def initModels():
	global model1
	model1.dataSource = NetworkModel.getOrCreateDataSource()
	model1.network = Network("network1.nta")
	#reset the dataSource
	model1.network.regions[_RECORD_SENSOR].dataSource = model1.dataSource
	
	"""
	global model2
	model2.dataSource = MultiLevelNetworkModel.getOrCreateDataSource()
	model2.network = LoadNetwork("network2.nta")
	#reset the dataSource
	model2.network.regions[_RECORD_SENSOR].dataSource = dataSource
	
	global model3
	model3.dataSource = MultiLevelNetworkAnomaly.getOrCreateDataSource()
	model3.network = LoadNetwork("network3.nta")
	#reset the dataSource
	model3.network.regions[_RECORD_SENSOR].dataSource = dataSource
	"""
	
def main():
	var_bootstrap_servers='172.25.130.9'+':9092'
	initModels()
	
	start = datetime.datetime.now()
	
	if len(sys.argv)==1:
		consumer = KafkaConsumer('HTMTestingData', group_id="TEST", bootstrap_servers=var_bootstrap_servers)
		for msg in consumer:
			runModel(msg.value)
	else:
		with open(_FILE_PATH, 'r') as f:
			for line in f:
				runModel(line)
	
	end = datetime.datetime.now()
	
	getModelStats()
	
	print("Time taken to test a model\n")
	print (end-start)
	
	
if __name__ == "__main__":
    main()
