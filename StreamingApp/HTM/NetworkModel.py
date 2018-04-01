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

# Seed used for random number generation
_SEED = 2045
_INPUT_FILE_PATH = "rec-center-hourly.csv";
_OUTPUT_FILE_NAME = "hierarchy-demo-output.csv"

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

_RECORD_SENSOR = "sensorRegion"
_L1_SPATIAL_POOLER = "l1SpatialPoolerRegion"
_L1_TEMPORAL_MEMORY = "l1TemporalMemoryRegion"
_L1_CLASSIFIER = "l1Classifier"

_L2_SPATIAL_POOLER = "l2SpatialPoolerRegion"
_L2_TEMPORAL_MEMORY = "l2TemporalMemoryRegion"
_L2_CLASSIFIER = "l2Classifier"



def createEncoder():
  """
  Creates and returns a #MultiEncoder including a ScalarEncoder for
  energy consumption and a DateEncoder for the time of the day.
  @see nupic/encoders/__init__.py for type to file-name mapping
  @see nupic/encoders for encoder source files
  """
  encoder = MultiEncoder()
  encoder.addMultipleEncoders({
      "consumption": {"fieldname": u"cpu",
                      "type": "ScalarEncoder",
                      "name": u"cpu",
                      "minval": 0.0,
                      "maxval": 100.0,
                      "clipInput": True,
                      "w": 21,
                      "n": 500}})
  return encoder



def createRecordSensor(network, name, dataSource):
  """
  Creates a RecordSensor region that allows us to specify a file record
  stream as the input source.
  """

  # Specific type of region. Possible options can be found in /nupic/regions/
  regionType = "py.RecordSensor"

  # Creates a json from specified dictionary.
  regionParams = json.dumps({"verbosity": _VERBOSITY})
  network.addRegion(name, regionType, regionParams)

  # getSelf returns the actual region, instead of a region wrapper
  sensorRegion = network.regions[name].getSelf()

  # Specify how RecordSensor encodes input values
  sensorRegion.encoder = createEncoder()

  # Specify which sub-encoder should be used for "actValueOut"
  network.regions[name].setParameter("predictedField", "cpu")

  # Specify the dataSource as a file record stream instance
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



def createNetwork(dataSource):
  """Creates and returns a new Network with a sensor region reading data from
  'dataSource'. There are two hierarchical levels, each with one SP and one TM.
  @param dataSource - A RecordStream containing the input data
  @returns a Network ready to run
  """
  network = Network()

  # Create and add a record sensor and a SP region
  sensor = createRecordSensor(network, name=_RECORD_SENSOR,
                              dataSource=dataSource)
  createSpatialPooler(network, name=_L1_SPATIAL_POOLER,
                      inputWidth=sensor.encoder.getWidth())

  # Link the SP region to the sensor input
  linkType = "UniformLink"
  linkParams = ""
  network.link(_RECORD_SENSOR, _L1_SPATIAL_POOLER, linkType, linkParams)

  # Create and add a TM region
  l1temporalMemory = createTemporalMemory(network, _L1_TEMPORAL_MEMORY)

  # Link SP region to TM region in the feedforward direction
  network.link(_L1_SPATIAL_POOLER, _L1_TEMPORAL_MEMORY, linkType, linkParams)

  # Add a classifier
  classifierParams = {  # Learning rate. Higher values make it adapt faster.
                        'alpha': 0.005,

                        # A comma separated list of the number of steps the
                        # classifier predicts in the future. The classifier will
                        # learn predictions of each order specified.
                        'steps': '1,2',#,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20, 21,22,23,24,25,26,27,28,29,30',

                        # The specific implementation of the classifier to use
                        # See SDRClassifierFactory#create for options
                        'implementation': 'py',

                        # Diagnostic output verbosity control;
                        # 0: silent; [1..6]: increasing levels of verbosity
                        'verbosity': 0}

  l1Classifier = network.addRegion(_L1_CLASSIFIER, "py.SDRClassifierRegion",
                                   json.dumps(classifierParams))
  l1Classifier.setParameter('inferenceMode', True)
  l1Classifier.setParameter('learningMode', True)
  network.link(_L1_TEMPORAL_MEMORY, _L1_CLASSIFIER, linkType, linkParams,
               srcOutput="bottomUpOut", destInput="bottomUpIn")
  network.link(_RECORD_SENSOR, _L1_CLASSIFIER, linkType, linkParams,
               srcOutput="categoryOut", destInput="categoryIn")
  network.link(_RECORD_SENSOR, _L1_CLASSIFIER, linkType, linkParams,
               srcOutput="bucketIdxOut", destInput="bucketIdxIn")
  network.link(_RECORD_SENSOR, _L1_CLASSIFIER, linkType, linkParams,
               srcOutput="actValueOut", destInput="actValueIn")

  # Second Level
  l2inputWidth = l1temporalMemory.getSelf().getOutputElementCount("bottomUpOut")
  createSpatialPooler(network, name=_L2_SPATIAL_POOLER, inputWidth=l2inputWidth)
  network.link(_L1_TEMPORAL_MEMORY, _L2_SPATIAL_POOLER, linkType, linkParams)

  createTemporalMemory(network, _L2_TEMPORAL_MEMORY)
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
  return network

""" global data counter """
numRecords=0
l1PreviousPredictedColumns = []
l2PreviousPredictedColumns = []
l1PreviousPrediction = None
l2PreviousPrediction = None
l1ErrorSum = 0.0
l2ErrorSum = 0.0

def run(network):
    global numRecords
    numRecords = numRecords + 1;
    sensorRegion = network.regions[_RECORD_SENSOR]
    l1SpRegion = network.regions[_L1_SPATIAL_POOLER]
    l1TpRegion = network.regions[_L1_TEMPORAL_MEMORY]
    l1Classifier = network.regions[_L1_CLASSIFIER]
    
    l2SpRegion = network.regions[_L2_SPATIAL_POOLER]
    l2TpRegion = network.regions[_L2_TEMPORAL_MEMORY]
    l2Classifier = network.regions[_L2_CLASSIFIER]
    
    global l1PreviousPredictedColumns
    global l2PreviousPredictedColumns
    
    global l1PreviousPrediction, l2PreviousPrediction
    global l1ErrorSum, l2ErrorSum
    
    network.run(1)
    """actual = json.loads(jsonData)["cpu_metric"]"""
    
    actual = float(sensorRegion.getOutputData("actValueOut")[0])
    l1Result = getPredictionResults(l1Classifier)
    steps = l1Classifier.getSelf().stepsList
    
    l1Prediction = l1Result[steps[0]]["predictedValue"]     
    if l1PreviousPrediction is not None:
            l1ErrorSum += math.fabs(l1PreviousPrediction - actual)
    
    l1PreviousPrediction = l1Prediction

    l2Result = getPredictionResults(l2Classifier)
    l2Prediction = l2Result[steps[0]]["predictedValue"]
    
    if l2PreviousPrediction is not None:
        l2ErrorSum += math.fabs(l2PreviousPrediction - actual)
    l2PreviousPrediction = l2Prediction

    l1AnomalyScore = l1TpRegion.getOutputData("anomalyScore")[0]
    l2AnomalyScore = l2TpRegion.getOutputData("anomalyScore")[0]

    # Write record number, actualInput, and anomaly scores
    # writer.writerow((record, actual, l1PreviousPrediction, l1AnomalyScore, l2PreviousPrediction, l2AnomalyScore))

    print("record="+ str(numRecords) + ", actual=" + str(actual) + "l1PreviousPrediction" + str(l1PreviousPrediction) + "l2PreviousPrediction"+ str(l2PreviousPrediction))

    for i in range(len(steps)):
        print("Step"+ str(steps[i]) +": l1Prediction" + str(l1Result[steps[i]]["predictedValue"] ) + ", l2Prediction"+ str(l2Result[steps[i]]["predictedValue"] ))


    # Store the predicted columns for the next timestep
    l1PredictedColumns = l1TpRegion.getOutputData("topDownOut").nonzero()[0]
    l1PreviousPredictedColumns = copy.deepcopy(l1PredictedColumns)
    #
    l2PredictedColumns = l2TpRegion.getOutputData("topDownOut").nonzero()[0]
    l2PreviousPredictedColumns = copy.deepcopy(l2PredictedColumns)

  # Output absolute average error for each level
    if numRecords > 1:
        print("L1 ave abs class. error: %f" % (l1ErrorSum / (numRecords - 1)))
        print("L2 ave abs class. error: %f" % (l2ErrorSum / (numRecords - 1)))
    

def getPredictionResults(classifierRegion):
    """Helper function to extract results for all prediction steps."""
    
    actualValues = classifierRegion.getOutputData("actualValues")
    probabilities = classifierRegion.getOutputData("probabilities")
    steps = classifierRegion.getSelf().stepsList

    N = classifierRegion.getSelf().maxCategoryCount
    results = {step: {} for step in steps}
    for i in range(len(steps)):
        # stepProbabilities are probabilities for this prediction step only.
        stepProbabilities = probabilities[i * N:(i + 1) * N - 1]
        mostLikelyCategoryIdx = stepProbabilities.argmax()
        predictedValue = actualValues[mostLikelyCategoryIdx]
        predictionConfidence = stepProbabilities[mostLikelyCategoryIdx]
        results[steps[i]]["predictedValue"] = predictedValue
        results[steps[i]]["predictionConfidence"] = predictionConfidence
    return results


def runNetwork(network, numRecords, dataSource):
    flag =1;
    print(dir(network.regions[_RECORD_SENSOR]))
    print(dataSource.getNextRecord(useCache=False))
    while(flag == 1):
        run(network)
        flag = input("Continue? 1/0 ")
        if(flag == 2):
            l=[]
            l.append("7/2/2010 0:00")
            l.append("51.00")
            dataSource.rewind()
            flag =1
        

def runDemo():
    fields = ['cpu']
    dataSource = kafkaRecordStream(streamName=_INPUT_FILE_PATH, fields=fields)
    
    numRecords = dataSource.getDataRowCount()
    print("Creating network")
    network = createNetwork(dataSource)
    outputPath = os.path.join(os.path.dirname(__file__), _OUTPUT_FILE_NAME)
    
    with open(outputPath, "w") as outputFile:
        writer = csv.writer(outputFile)
        print("Running network")
        print("Writing output to: %s" % outputPath)
        runNetwork(network, numRecords, dataSource)
    
    print("Hierarchy demo finished")



if __name__ == "__main__":
  runDemo()
