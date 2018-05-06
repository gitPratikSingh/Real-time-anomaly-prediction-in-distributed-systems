
### System Setting
![AWS Architectures](https://github.com/atambol/Real-time-anomaly-prediction-in-distributed-systems/blob/master/AWS_Architecture.png?raw=true "AWS_Architectures")

##### Overview of the distributed architecture:
* The system under observation here is a Rubis cluster that consists of a web server, a database server and multiple clients.
* The clients generate a workload that consist of 75 percent browse requests.
* Two important characteristic of the system are collected during this:
    * Web server CPU and memory usage
    * Response time for clients to get each request serviced by the web server.
* Both these characteristics are produced on to two topics on Kafka.
* These characteristics are aggregated into data points per second to allow HTM engine to consume them.
* Aggregation includes following steps:
    * Consuming messages from the metrics and response time topics.
    * Metrics topic contains messages for each epoch (per second)
    * Response time topic contains messages for each request made by each of the clients. This implies multiple messages per epoch.
    * For each epoch, calculate the average and maximum response time and combine that with CPU and memory usage. Also calculate any response time exceeds an acceptable amount for that interval.
    * Produce this aggregated message on a new topic.
* HTM engine consumes these messages and predicts based on the trained model if or not an SLO violation is going to occur with some lead time. 

##### Cloudformation:
* The whole infrastructure is maintained as Infrastructure as Code using AWS Cloudformation template programmed in Python.
* Single click deployment of the setup is possible within 15 minutes time.
* Creating Stack : run `python create_stack.py`
* Resources created include: 
    * VPC
    * gateway
    * route tables and routes
    * public and private subnets
    * Security groups
    * Multiple Instances:
        * NAT
        * Kafka
        * Rubis database
        * Rubis web server
        * Rubis clients
        * HTM engine
* All the public traffic goes through NAT. No other instance can be accessed directly from internet. This saved both cost of assigning each instance with a public IP and acts as an added security features.

##### RUBiS
* [RUBiS Repository](https://github.com/atambol/RUBiS)
* Current installation creates following types of instances for RUBiS: 
    * Rubis Clients
    * DB Server
    * Web Server
* Rubis Web Server UI: http://<NAT's Public IP>:8080/PHP/index.html

##### Kafka
* Kafka Broker UI: http://<NAT's Public IP>:3030
* System metrics topic name: `stats`
* Response time topic name: `responsetime`
* Aggregated metrics and response time topic (calculated per second): `aggregate`

##### Anomaly injection
Anomaly is generated using a script that hogs on the CPU in the web server. This higging slowly increases and eventually web server cannot allot sufficient CPU time to web requests. This is the point when the requests start to get longer response times and SLO violations can be therefore triggered using this trick. 

##### IP addresses of instances in the private network:
* nat: 172.25.0.5
* db: 172.25.130.7
* web_server: 172.25.130.8
* kafka: 172.25.130.9
* htm: 172.25.130.10
* rubis_client1: 172.25.130.11
* rubis_client2: 172.25.130.12
* rubis_client3: 172.25.130.13
* rubis_client4: 172.25.130.14
* rubis_client5: 172.25.130.15




##### Model 
* 1. Training: How to train?
   Option1. Place Training.txt in the Data directory, run, python ModelTraining.py file
   Option2. To read training data from Kafka topic, run, python ModelTraining.py   

* 2. Testing: How to test?
   Option1. Place Testing.txt in the Data directory, run, python ModelTesting.py file
   Option2. To read training data from Kafka topic, run, python ModelTesting.py   

The Training phase, builds 3 models from scratch and saves them in "network[placeholder(model#)].nta" as a pickle file.
The Testing phase recreates these models from the pickle files and uses them for testing.

* Model 1: 
	AnomalyScoreThreshold = 0.98
	Avg leadtime 12.0 secs
	Model accuracy : 95.91 %
	
* Model 2:
	AnomalyScoreThreshold = 0.99
	Avg leadtime 43.77 secs
	Model accuracy: 4.74 %

* Model 3:
  AnomalyScoreThreshold = 0.99
	Avg leadtime 46.45 secs
	Model accuracy: 4.75 %
	
	
Model 1 seems to be working fine. But Model 2 and Model 3 predict anomaly very frequently(very high percentage of False Positives). Model 2,3 very frequently give anomaly scores close to 1 even for non-anomalous data. 

How the model works: 
1. The models first learns on the training data. I enabled the inference/learning mode of spatial pooler and temporary memory during training. The model is configured using model params, to provide 7 steps ahead predictions as well. The model is trained on non-anomalous data

2. At the end of the training phase, the models are saved in pickle files for later use.

3. In the testing phase, the models are recreated from the pickle files. Each model consumes the current input from the stream(with inference mode ON),and provides the next 7 steps predictions. Then each model is fed the predicted 7 steps(with inference mode OFF), which gives us the future anomalous score values. When any of the future anomaly scores are greater than anomalyscore threshold, then the model predicts an anomaly.

4. In the testing phase, CPU anomaly is introduced at different instances in the testing stream data. We injected this bug 53 times during the half hour RUBiS simulation. In CPU anomaly, we know that it takes 50 secs on an average to make the current state anomalous.
Say the CPU anomaly was introduced at t1, then after t1+50 sec, SLO violations will occur. We observed this value(50sec) by running it many time and observing the SLO feedback stream.

5. The main thread maintains a list(predictionList in ModelTesting.py) to identify when the model predicted an anomaly. Using the SLO Violation feedback, the 
thread updates the predictionList and classifies the predictions into TP, FP, TN, FN.

	a) A prediction is TP, if the model predicted anomaly it at t1, and SLO violation(s) occur during (t1, t1+50).
	b) A prediction is FP, if the model predicted anomaly it at t1, and no SLO violations occur during (t1, t1+50).
	c) A prediction is TN, if the model does not predicted any anomaly at t1, and no SLO violations occur during (t1, t1+50).
	d) A prediction is FN, if the model does not predicted any anomaly at t1, and SLO violation(s) occur during (t1, t1+50).


#We were not able to produce SLO violations due memory leak. We observed that even when the web server's memory was full, the SLO violations does not occur. Normal workload's memory consumption was 30%. We introduced the memoryleak and the memory usage went up (95-100%), but no SLO violations. We were not able to figure out the issue. We expected to see a lot of SLO violations when memory utilization was >= 90%.    




##### Notes:
* Private key to access NAT : 724_keypair.pem
* Ensure NatS3Access IAM role is created before running this template
* HTM instance uses a pre-baked AMI
* The aggregation is performed in the NAT instance and need to be manually started when workload is being simulated.
* References: 
    * [Optimizing CFN templates](https://aws.amazon.com/blogs/devops/optimize-aws-cloudformation-templates/)
    * [LAMP stack installation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-LAMP.html)
    
    

