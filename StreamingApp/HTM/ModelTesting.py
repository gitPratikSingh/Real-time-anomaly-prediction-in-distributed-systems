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

_RECORD_SENSOR = "sensorRegion"

model1 = lambda: None
model2 = lambda: None
model3 = lambda: None

model1.tp = 0
model1.fp = 0
model1.tn = 0
model1.fn = 0

_SLO_CPU=65
_ANOMALY_SCORE=0.5

def runModel(jsonData):
	global model1
	global model2
	global model3

	cpuSLOViolationPredictions=0
	AnomalyScoreViolation=0
	
	print("RunMethod" + str(jsonData))
	cpuMetric = float(json.loads(jsonData)['cpu'])
	memMetric = float(json.loads(jsonData)['mem'])
	WasSloviolation = float(json.loads(jsonData)['slo'])
	
	actualVal, predictions, errorVal, anomalyScore = NetworkModel.runNetwork(model1.network, model1.dataSource, cpuMetric, True)
	
	if anomalyScore > _ANOMALY_SCORE:
		#check to see if there is any anomaly for this dataset
		if WasSloviolation==1:
			# true positive
			model1.tp = model1.tp + 1
		else:
			# false positive	
			model1.tp = model1.tp + 1
	else: 
		if WasSloviolation == 0:
			# true negative
			model1.tn = model1.tn + 1
		else:
			# false negative	
			model1.fp = model1.fp + 1
	
	"""
	if all(prediction < _SLO_CPU for prediction in predictions) == False:
		cpuSLOViolationPredictions=cpuSLOViolationPredictions+1
	
	if anomalyScore > _ANOMALY_SCORE:
		AnomalyScoreViolation = AnomalyScoreViolation + 1
	
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
	
	# Raise alarm only when both satisfy
	if AnomalyScoreViolation > 0 and cpuSLOViolationPredictions > 0:
		raiseAlarm()
	"""
def raiseAlarm():
	print("Alarm raised!")
	
def initModels():
	global model1
	model1.dataSource = NetworkModel.getOrCreateDataSource()
	model1.network = LoadNetwork("network1.nta")
	#reset the dataSource
	model1.network.regions[_RECORD_SENSOR].dataSource = dataSource
	
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
	
def main():
	var_bootstrap_servers=sys.argv[1]+':9092'
	initModels()
	
	consumer = KafkaConsumer('HTMTestingData', group_id="TEST", bootstrap_servers=var_bootstrap_servers)
	global model1
	
	for msg in consumer:
		runModel(msg.value)
		print(model1)
		
if __name__ == "__main__":
    main()
