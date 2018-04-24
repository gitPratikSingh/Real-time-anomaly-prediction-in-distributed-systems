import copy
import csv
import json
import os
import math
import numpy

from pkg_resources import resource_filename

from nupic.data.file_record_stream import FileRecordStream
from nupic.engine import Network
from nupic.encoders import MultiEncoder

from StreamReader import kafkaRecordStream
# Level of detail of console output. Int value from 0 (none)
# to 3 (super detailed)
_VERBOSITY = 0
_STREAM_NAME = "KAFKA"
# Seed used for random number generation
_SEED = 2045

# Parameter dict for SPRegion
SP_PARAMS = {"spVerbosity": _VERBOSITY,
             "spatialImp": "cpp",
             "seed": _SEED,

             # determined and set during network creation
             "inputWidth": 0,

             # @see nupic.research.spatial_pooler.SpatialPooler for explanations
             "globalInhibition": 1,
             "columnCount": 2048,
             "numActiveColumnsPerInhArea": 40,
             "potentialPct": 0.8,
             "synPermConnected": 0.1,
             "synPermActiveInc": 0.0001,
             "synPermInactiveDec": 0.0005,
             "boostStrength": 0.0}

# Parameter dict for TPRegion
TM_PARAMS = {"verbosity": _VERBOSITY,
             "temporalImp": "cpp",
             "seed": _SEED,

             # @see nupic.research.temporal_memory.TemporalMemory
             # for explanations
             "columnCount": 2048,
             "cellsPerColumn": 12,
             "inputWidth": 2048,
             "newSynapseCount": 20,
             "maxSynapsesPerSegment": 32,
             "maxSegmentsPerCell": 128,
             "initialPerm": 0.21,
             "permanenceInc": 0.1,
             "permanenceDec": 0.1,
             "globalDecay": 0.0,
             "maxAge": 0,
             "minThreshold": 9,
             "activationThreshold": 12,
             "outputType": "normal",
             "pamLength": 3}

dataSource = None
saveFrequency = 50

def getOrCreateDataSource(fields, names):
	global dataSource
	
	if dataSource is None:
		dataSource = kafkaRecordStream(streamName=_STREAM_NAME, fields=fields, names=names)
	
	return dataSource

def createEncoder(multilevelAnomaly=False):
	encoder = MultiEncoder()
	if multilevelAnomaly == False:
		encoder.addMultipleEncoders({
		"cpu": {"fieldname": u"cpu",
				"type": "ScalarEncoder",
				"name": u"cpu",
				"minval": 0.0,
				"maxval": 100.0,
				"clipInput": True,
				"w": 21,
				"n": 500}})
	else:
		encoder.addMultipleEncoders({
		"cpu": {"fieldname": u"cpu",
				"type": "ScalarEncoder",
				"name": u"cpu",
				"minval": 0.0,
				"maxval": 100.0,
				"clipInput": True,
				"w": 21,
				"n": 500},
		"mem": {"fieldname": u"mem",
				"type": "ScalarEncoder",
				"name": u"mem",
				"minval": 0.0,
				"maxval": 100.0,
				"clipInput": True,
				"w": 21,
				"n": 500}})

	return encoder
	

def createRecordSensor(network, name, dataSource, multilevelAnomaly=False):
  # sensor
  regionType = "py.RecordSensor"
  regionParams = json.dumps({"verbosity": _VERBOSITY})
  network.addRegion(name, regionType, regionParams)
  sensorRegion = network.regions[name].getSelf()
  #encoder
  sensorRegion.encoder = createEncoder(multilevelAnomaly)
  network.regions[name].setParameter("predictedField", "cpu")
  sensorRegion.dataSource = dataSource
  
  return sensorRegion



def createSpatialPooler(network, name, inputWidth):
  # Create the spatial pooler region
  SP_PARAMS["inputWidth"] = inputWidth
  spatialPoolerRegion = network.addRegion(name, "py.SPRegion",
                                          json.dumps(SP_PARAMS))
  # Make sure learning is enabled
  spatialPoolerRegion.setParameter("learningMode", True)
  # We want temporal anomalies so disable anomalyMode in the SP. This mode is
  # used for computing anomalies in a non-temporal model.
  spatialPoolerRegion.setParameter("anomalyMode", False)
  return spatialPoolerRegion



def createTemporalMemory(network, name):
  temporalMemoryRegion = network.addRegion(name, "py.TMRegion",
                                           json.dumps(TM_PARAMS))
  # Enable topDownMode to get the predicted columns output
  temporalMemoryRegion.setParameter("topDownMode", True)
  # Make sure learning is enabled (this is the default)
  temporalMemoryRegion.setParameter("learningMode", True)
  # Enable inference mode so we get predictions
  temporalMemoryRegion.setParameter("inferenceMode", True)
  # Enable anomalyMode to compute the anomaly score. This actually doesn't work
  # now so doesn't matter. We instead compute the anomaly score based on
  # topDownOut (predicted columns) and SP bottomUpOut (active columns).
  temporalMemoryRegion.setParameter("anomalyMode", True)
  return temporalMemoryRegion


def SaveNetwork(network, name):
	savePath = os.path.join(os.getcwd(), name)
	network.save(savePath)
	return savePath

def LoadNetwork(savePath):
	net = Network(savePath)
	return net
	

def getPredictionResults(classifierRegion):
    """Helper function to extract results for all prediction steps."""
    
    actualValues = classifierRegion.getOutputData("actualValues")
    probabilities = classifierRegion.getOutputData("probabilities")
    steps = classifierRegion.getSelf().stepsList

    N = classifierRegion.getSelf().maxCategoryCount
    results = []
    confidence = []
    for i in range(len(steps)):
        # stepProbabilities are probabilities for this prediction step only.
        stepProbabilities = probabilities[i * N:(i + 1) * N - 1]
        mostLikelyCategoryIdx = stepProbabilities.argmax()
        predictedValue = actualValues[mostLikelyCategoryIdx]
        predictionConfidence = stepProbabilities[mostLikelyCategoryIdx]
        results.append(predictedValue)
        confidence.append(predictionConfidence)
    return results, confidence

