import csv
import datetime
import numpy
import os
import yaml
import json

from nupic.algorithms.sdr_classifier_factory import SDRClassifierFactory
from nupic.algorithms.spatial_pooler import SpatialPooler
from nupic.algorithms.temporal_memory import TemporalMemory
from nupic.encoders.random_distributed_scalar import RandomDistributedScalarEncoder

_NUM_RECORDS = 13000
_EXAMPLE_DIR = os.path.dirname(os.path.abspath(__file__))
_INPUT_FILE_PATH = os.path.join(_EXAMPLE_DIR, "data", "gymdata.csv")
_PARAMS_PATH = os.path.join(_EXAMPLE_DIR, "params", "model.yaml")


class Model:
    
    def __init__(self):
        self.BuildModel()
        
    def BuildModel(self):
        with open(_PARAMS_PATH, "r") as f:
            self.modelParams = yaml.safe_load(f)["modelParams"]
            self.enParams = self.modelParams["sensorParams"]["encoders"]
            self.spParams = self.modelParams["spParams"]
            self.tmParams = self.modelParams["tmParams"]
        
        scalarEncoder = RandomDistributedScalarEncoder(
            self.enParams["cpu_metric"]["resolution"])
        
        encodingWidth = (scalarEncoder.getWidth())
        
        print(encodingWidth)
        
        sp = SpatialPooler(
            inputDimensions=(encodingWidth,),
            columnDimensions=(self.spParams["columnCount"],),
            potentialPct=self.spParams["potentialPct"],
            potentialRadius=encodingWidth,
            globalInhibition=self.spParams["globalInhibition"],
            localAreaDensity=self.spParams["localAreaDensity"],
            numActiveColumnsPerInhArea=self.spParams["numActiveColumnsPerInhArea"],
            synPermInactiveDec=self.spParams["synPermInactiveDec"],
            synPermActiveInc=self.spParams["synPermActiveInc"],
            synPermConnected=self.spParams["synPermConnected"],
            boostStrength=self.spParams["boostStrength"],
            seed=self.spParams["seed"],
            wrapAround=True
        )
        
        
        tm = TemporalMemory(
            columnDimensions=(self.tmParams["columnCount"],),
            cellsPerColumn=self.tmParams["cellsPerColumn"],
            activationThreshold=self.tmParams["activationThreshold"],
            initialPermanence=self.tmParams["initialPerm"],
            connectedPermanence=self.spParams["synPermConnected"],
            minThreshold=self.tmParams["minThreshold"],
            maxNewSynapseCount=self.tmParams["newSynapseCount"],
            permanenceIncrement=self.tmParams["permanenceInc"],
            permanenceDecrement=self.tmParams["permanenceDec"],
            predictedSegmentDecrement=0.0,
            maxSegmentsPerCell=self.tmParams["maxSegmentsPerCell"],
            maxSynapsesPerSegment=self.tmParams["maxSynapsesPerSegment"],
            seed=self.tmParams["seed"]
        )
        
        classifier = SDRClassifierFactory.create()
        
        self.count = 0;
        self.sp = sp
        self.tm = tm
        self.classifier = classifier
        self.scalarEncoder = scalarEncoder
        
        
    def run(self, jsonData):
        
        print(jsonData)
        _dict = json.loads(jsonData)
        
        # Convert data value string into float.
        cpuMetric = float(_dict["cpu_metric"])
        
        # To encode, we need to provide zero-filled numpy arrays for the encoders
        # to populate.
        cpuMetricBits = numpy.zeros(self.scalarEncoder.getWidth())
        
        # Now we call the encoders to create bit representations for each value.
        self.scalarEncoder.encodeIntoArray(cpuMetric, cpuMetricBits)
        
        # Concatenate all these encodings into one large encoding for Spatial
        # Pooling.
        encoding = numpy.concatenate(
          [cpuMetricBits]
        )
    
        # Create an array to represent active columns, all initially zero. This
        # will be populated by the compute method below. It must have the same
        # dimensions as the Spatial Pooler.
        activeColumns = numpy.zeros(self.spParams["columnCount"])
        
        # Execute Spatial Pooling algorithm over input space.
        self.sp.compute(encoding, True, activeColumns)
        activeColumnIndices = numpy.nonzero(activeColumns)[0]
        
        # Execute Temporal Memory algorithm over active mini-columns.
        self.tm.compute(activeColumnIndices, learn=True)
        
        activeCells = self.tm.getActiveCells()
        
        # Get the bucket info for this input value for classification.
        bucketIdx = self.scalarEncoder.getBucketIndices(cpuMetric)[0]
        
        self.count = self.count + 1
        # Run classifier to translate active cells back to scalar value.
        classifierResult = self.classifier.compute(
          recordNum=self.count,
          patternNZ=activeCells,
          classification={
            "bucketIdx": bucketIdx,
            "actValue": cpuMetric
          },
          learn=True,
          infer=True
        )
    
        # Print the best prediction for 1 step out.
        oneStepConfidence, oneStep = sorted(zip(classifierResult[1], classifierResult["actualValues"]), reverse=True)[0]
        
        print("1-step: {:16} ({:4.4}%)".format(oneStep, oneStepConfidence * 100))
        


if __name__ == "__main__":
    model = Model()
    for i in range(1000):
        model.run("""{"cpu_metric": 58}""")
        model.run("""{"cpu_metric": 68}""")
        model.run("""{"cpu_metric": 78}""")
        
