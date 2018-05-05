#!/usr/bin/env python

# Author: Pratik Singh
# Description: Instantiates the saved Models(I,II,III) and it can consume data directly from kafka stream or file

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
_FILE_PATH = "../../ML/TestingData.txt"

model1 = lambda: None
model2 = lambda: None
model3 = lambda: None

model1.tp = 0
model1.fp = 0
model1.tn = 0
model1.fn = 0

_ANOMALY_SCORE=0.85
_MAX_LEAD_TIME = 50
_SLO_RESPONSE_TIME = 70

predictionList = list()
rcount=0
def runModel(jsonData, printflag):
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
	
	
	actualVal, predictions, errorVal, anomalyScore = NetworkModel.runNetwork(model1.network, model1.dataSource, cpuMetric, True, True)
	anomalywindow.append(anomalyScore)
	
	# find the future anomaly scores as well
	for prediction in predictions:
		x, y, z, anomalyScore = NetworkModel.runNetwork(model1.network, model1.dataSource, cpuMetric, False, False)
		anomalywindow.append(anomalyScore)
	
	
	for anomaly in anomalywindow:
		if anomaly > _ANOMALY_SCORE:
			AnomalyScoreViolation = AnomalyScoreViolation + 1
		
	
	# Raise alarm only when this satisfy
	if AnomalyScoreViolation > 0 and rcount > 1:
		if printflag == True:
			raiseAlarm(1, rcount)

		anomaly = list()
		anomaly.append(-1)
		anomaly.append('A')
		anomaly.append(rcount)
		anomaly.append('TP')
		anomaly.append(0)
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
		if printflag == True:
			print("SLO violation at "+str(timenow)+" for record number "+ str(rcount))
	else:
		processpredictionList('N', rcount)
	
	
def raiseAlarm(modelId, recId):
	print("Alarm raised by - Model " +str(modelId) + " at "+ str(int(time.time()))+" for recID "+ str(recId))
	
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
						item[4] = _MAX_LEAD_TIME - (rcount - item[2])
						
						if rcount - _MAX_LEAD_TIME>0: 
							start = rcount - _MAX_LEAD_TIME 
						else: 
							start = 0
 
						for nelem in predictionList[start:rcount]:				
							if nelem[3] == 'FN' :
								nelem[3] = 'TN'
								
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
	leadTime = 0.0
	for item in predictionList[:-_MAX_LEAD_TIME]:
		if item[3] == 'TP':
			tp += 1
			leadTime += item[4]
		if item[3] == 'TN':
			tn += 1
		if item[3] == 'FP':
			fp += 1
		if item[3] == 'FN':
			fn += 1
	
	print("TP: "+str(tp) + " FP: "+str(fp) + " TN: "+str(tn) + " FN: "+str(fn))

	if tp != 0:
		print("Avg leadtime "+str(leadTime/tp))	

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
	
	count = 0
	if len(sys.argv)==1:
		consumer = KafkaConsumer('aggregate', bootstrap_servers=var_bootstrap_servers, auto_offset_reset='latest')
		for msg in consumer:
			runModel(msg.value, True)
			count += 1
			
			if count%60 == 0:
				getModelStats()

	else:
		with open(_FILE_PATH, 'r') as f:
			for line in f:
				runModel(line, False)
	
	end = datetime.datetime.now()
	
	getModelStats()
	
	print("Time taken to test a model\n")
	print (end-start)
	
	
if __name__ == "__main__":
    main()
