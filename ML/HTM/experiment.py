import shutil
import csv

import generate_data
from nupic.swarming import permutations_runner

from nupic.frameworks.opf.model_factory import ModelFactory
from nupic_output import NuPICFileOutput, NuPICPlotOutput

# Change this to switch from a matplotlib plot to file output.
PLOT = True

def swarm_over_data():
	swarm_config={
		"includedFields":[
			{
				"fieldName":"sine",
				"fieldType":"float",
				"maxValue":1.0,
				"minValue":-1.0
			}	
		],
		"streamDef":{
			"info":"sine",
			"version":1,
			"streams":[
				{
					"info":"sine.csv",
					"source":"file://sine.csv",
					"columns":["*"]
				}		
			]
		},
		"inferenceType":"TemporalAnomaly",
		"inferenceArgs":{
			"predictionSteps":[
				1
			],
			"predictedField":"sine"	
		},
		"swarmSize":"medium"
	}
 

	model_params = permutations_runner.runWithConfig(swarm_config,
	      {'maxWorkers': 8, 'overwrite': True})
	shutil.copyfile("model_0/model_params.py", "model_params.py")


def run_experiment():
	generate_data.run()
	swarm_over_data()
	import model_params
	model = ModelFactory.create(model_params.MODEL_PARAMS)
	model.enableInference({"predictedField":"sine"})
	
	if PLOT:
		output = NuPICPlotOutput("sine_output", show_anomaly_score=True)
	else:
		output = NuPICFileOutput("sine_output", show_anomaly_score=True)

	with open("sine.csv", "rb") as sine_input:
		csv_reader = csv.reader(sine_input)

		#skip headers
		csv_reader.next()
		csv_reader.next()
		csv_reader.next()

		#real data
		for row in csv_reader:
			angle = float(row[0])
			sine_value = float(row[1])
			result = model.run({"sine": sine_value})
			output.write(angle, sine_value, result, prediction_step=1)
		
		output.close()

if __name__=="__main__":
	run_experiment()

