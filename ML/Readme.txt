
1. Training: How to train?
   Option1. Place Training.txt in the Data directory, run, python ModelTraining.py file
   Option2. To read training data from Kafka topic, run, python ModelTraining.py   

2. Testing: How to test?
   Option1. Place Testing.txt in the Data directory, run, python ModelTesting.py file
   Option2. To read training data from Kafka topic, run, python ModelTesting.py   

The Training phase, builds 3 models from scratch and saves them in "network[placeholder(model#)].nta" as a pickle file.
The Testing phase recreates these models from the pickle files and uses them for testing.

Model 1: 
	AnomalyScoreThreshold = 0.98
	Avg leadtime 12.0
	Model accuracy : 95.91 %

	
Model 2:
	AnomalyScoreThreshold = 0.99
	Avg leadtime 43.77
	Model accuracy: 4.74 %

	
Model 3:  
	AnomalyScoreThreshold = 0.99
	Avg leadtime 46.45
	Model accuracy: 4.75 %
	
	
Model 1 seems to be working fine. But Model 2 and Model 3 predict anomaly very frequently(very high percentage of False Positives). Model 2,3 very frequently give anomaly scores close to 1 even for non-anomalous data. 

How the model works: 
1. The models first learns on the training data. I enabled the inference/learning mode of spatial pooler and temporary memory during training.
The model is configured using model params, to provide 7 steps ahead predictions as well. The model is trained on non-anomalous data

2. At the end of the training phase, the models are saved in pickle files for later use.

3. In the testing phase, the models are recreated from the pickle files. Each model consumes the current input from the stream(with inference mode ON),
and provides the next 7 steps predictions. Then each model is fed the predicted 7 steps(with inference mode OFF), which gives us the future anomalous
score values. When any of the future anomaly scores are greater than anomalyscore threshold, then the model predicts an anomaly.

4. In the testing phase, CPU anomaly is introduced at different instances in the testing stream data. We injected this bug 53 times during
the half hour RUBiS simulation. In CPU anomaly, we know that it takes 50 secs on an average to make the current state anomalous. Say the CPU anomaly
was introduced at t1, then after t1+50 sec, SLO violations will occur. We observed this value(50sec) by running it many time and observing the SLO feedback
stream.

5. The main thread maintains a list(predictionList in ModelTesting.py) to identify when the model predicted an anomaly. Using the SLO Violation feedback, the 
thread updates the predictionList and classifies the predictions into TP, FP, TN, FN.

	a) A prediction is TP, if the model predicted anomaly it at t1, and SLO violation(s) occur during (t1, t1+50).
	b) A prediction is FP, if the model predicted anomaly it at t1, and no SLO violations occur during (t1, t1+50).
	c) A prediction is TN, if the model does not predicted any anomaly at t1, and no SLO violations occur during (t1, t1+50).
	d) A prediction is FN, if the model does not predicted any anomaly at t1, and SLO violation(s) occur during (t1, t1+50).


# We were not able to produce SLO violations due memory leak. We observed that even when the web server's memory was full, the SLO violations
does not occur. Normal workload's memory consumption was 30%. We introduced the memoryleak and the memory usage went up (95-100%), but no SLO
violations. We were not able to figure out the issue. We expected to see a lot of SLO violations when memory utilization was >= 90%.    

