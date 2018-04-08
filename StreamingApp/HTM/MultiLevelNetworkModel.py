import os
import numpy
import json
import math
from nupic.engine import Network

import NetworkUtils

""" global data """
numRecords=0
_RECORD_SENSOR = "sensorRegion"
_L1_SPATIAL_POOLER = "l1SpatialPoolerRegion"
_L1_TEMPORAL_MEMORY = "l1TemporalMemoryRegion"
_L1_CLASSIFIER = "l1Classifier"

_L2_SPATIAL_POOLER = "l2SpatialPoolerRegion"
_L2_TEMPORAL_MEMORY = "l2TemporalMemoryRegion"
_L2_CLASSIFIER = "l2Classifier"

w, h = 8, 7
results = [[-1 for x in range(w)] for y in range(h)] 
l2ErrorSum = [-1 for x in range(h)]


def getOrCreateDataSource():
	fields=[]
	fields.append('cpu')
	names = []
	names.append('cpu')
	return NetworkUtils.getOrCreateDataSource(fields, names)
	
def BuildNetwork():	
	dataSource = getOrCreateDataSource()
	network = createMultiLevelNetwork(dataSource)
	return dataSource, network
	    
def runNetwork(network, dataSource, data, disableTraining):
	
	#NetworkUtils.dataSource.data = data
	dataSource.setData(data)
	#dataSource.printData()
	if disableTraining == 1:
		network.regions[_L1_TEMPORAL_MEMORY].setParameter("learningMode", False)
		network.regions[_L1_CLASSIFIER].setParameter('learningMode', False)
		network.regions[_L2_TEMPORAL_MEMORY].setParameter("learningMode", False)
		network.regions[_L2_CLASSIFIER].setParameter('learningMode', False)
		
	return run(network)
    
def createMultiLevelNetwork(dataSource):
  
	network = Network()

	# Create and add a record sensor and a SP region
	sensor = NetworkUtils.createRecordSensor(network, name=_RECORD_SENSOR,
							  dataSource=dataSource)
	NetworkUtils.createSpatialPooler(network, name=_L1_SPATIAL_POOLER,
					  inputWidth=sensor.encoder.getWidth())

	# Link the SP region to the sensor input
	linkType = "UniformLink"
	linkParams = ""
	network.link(_RECORD_SENSOR, _L1_SPATIAL_POOLER, linkType, linkParams)

	# Create and add a TM region
	l1temporalMemory = NetworkUtils.createTemporalMemory(network, _L1_TEMPORAL_MEMORY)

	# Link SP region to TM region in the feedforward direction
	network.link(_L1_SPATIAL_POOLER, _L1_TEMPORAL_MEMORY, linkType, linkParams)

	# Add a classifier
	classifierParams = {  # Learning rate. Higher values make it adapt faster.
						'alpha': 0.005,

						# A comma separated list of the number of steps the
						# classifier predicts in the future. The classifier will
						# learn predictions of each order specified.
						'steps': '1,2,3,4,5,6,7',

						# The specific implementation of the classifier to use
						# See SDRClassifierFactory#create for options
						'implementation': 'py',

						# Diagnostic output verbosity control;
						# 0: silent; [1..6]: increasing levels of verbosity
						'verbosity': 0}

	# Second Level
	l2inputWidth = l1temporalMemory.getSelf().getOutputElementCount("bottomUpOut")
	NetworkUtils.createSpatialPooler(network, name=_L2_SPATIAL_POOLER, inputWidth=l2inputWidth)
	network.link(_L1_TEMPORAL_MEMORY, _L2_SPATIAL_POOLER, linkType, linkParams)

	NetworkUtils.createTemporalMemory(network, _L2_TEMPORAL_MEMORY)
	network.link(_L2_SPATIAL_POOLER, _L2_TEMPORAL_MEMORY, linkType, linkParams)

	l2Classifier = network.addRegion(_L2_CLASSIFIER, "py.SDRClassifierRegion",
								   json.dumps(classifierParams))
	l2Classifier.setParameter('inferenceMode', True)
	l2Classifier.setParameter('learningMode', True)
	network.link(_L2_TEMPORAL_MEMORY, _L2_CLASSIFIER, linkType, linkParams,
			   srcOutput="bottomUpOut", destInput="bottomUpIn")
	network.link(_RECORD_SENSOR, _L2_CLASSIFIER, linkType, linkParams,
			   srcOutput="categoryOut", destInput="categoryIn")
	network.link(_RECORD_SENSOR, _L2_CLASSIFIER, linkType, linkParams,
			   srcOutput="bucketIdxOut", destInput="bucketIdxIn")
	network.link(_RECORD_SENSOR, _L2_CLASSIFIER, linkType, linkParams,
			   srcOutput="actValueOut", destInput="actValueIn")
	
	#feed back connection
	network.link(_L2_TEMPORAL_MEMORY, _L1_SPATIAL_POOLER, linkType, linkParams,
			   srcOutput="topDownOut", destInput="topDownIn")
	
	steps = l2Classifier.getSelf().stepsList
	
	# initialize the results matrix, after the classifer has been defined
	w, h = len(steps), len(steps)+1
	global results
	results = [[-1 for x in range(w)] for y in range(h)] 
	global l2ErrorSum
	l2ErrorSum = [-1 for x in range(h)]
	
	#print("Length: "+str(len(steps)))
	
	return network

def run(network):
	global numRecords
	global l2ErrorSum

	numRecords = numRecords + 1
	sensorRegion = network.regions[_RECORD_SENSOR]
	l2SpRegion = network.regions[_L2_SPATIAL_POOLER]
	l2TpRegion = network.regions[_L2_TEMPORAL_MEMORY]
	l2Classifier = network.regions[_L2_CLASSIFIER]
	
	if numRecords%NetworkUtils.saveFrequency == 0:
		print("Saving the Model to file")
		NetworkUtils.SaveNetwork(network, "network2.nta")
	
	network.run(1)

	actual = float(sensorRegion.getOutputData("actValueOut")[0])
	l2Result, l2ResultConf = NetworkUtils.getPredictionResults(l2Classifier)
	steps = l2Classifier.getSelf().stepsList

	l2AnomalyScore = l2TpRegion.getOutputData("anomalyScore")[0]

	print("record="+ str(numRecords))

	maxSteps = len(steps)
	for i in range(maxSteps):
		#shift the records
		if results[numRecords%(maxSteps+1)][i] != -1:
			l2ErrorSum[i] += math.fabs(results[numRecords%(maxSteps+1)][i] - actual)
		
		r = (steps[i]+numRecords)%(maxSteps+1)
		results[r][i] = l2Result[i]

	print("Actual Value: "+str(actual))
	print("Predicted: "+ str(results[numRecords%(maxSteps+1)]))
	print("Average Error: "+ str([x / numRecords for x in l2ErrorSum]))
	print("Classifier Anomaly Score: "+ str(l2AnomalyScore))	
	print("\n")
	
	print("Current Predictions" + str(l2Result))
	
	return str(actual), results[numRecords%(maxSteps+1)], 
	str([x / numRecords for x in l2ErrorSum]), l2AnomalyScore

if __name__ == "__main__":
	dataSource, network = BuildNetwork()
	data = 54
	disableTraining = 0
	runNetwork(network, dataSource, data, disableTraining)
	print("done")
