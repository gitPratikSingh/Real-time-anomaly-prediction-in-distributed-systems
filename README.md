![Real-time anomaly prediction in distributed systems](https://github.com/gitPratikSingh/Real-time-anomaly-prediction-in-distributed-systems/blob/master/Capture.PNG?raw=true "Real-time anomaly prediction in distributed systems")

Topic: Anomaly detection & proactive fault management

Below is the timeline of events that happens in any proactive fault management technique

                    Time for prediction      Time for localization     Time for fault fixing
Error State<-----------------------------><---------------------------><----------------------------->Normal State

Objective: Implement FCHAIN/UBL/PREPARE & try to reduce time for any of the above three sub-states


###System components that we need to implement
* Cloud/cluster monitoring software for data collection
* Build SLA Prediction Model
* Detect SLA violations
* Fault localization
* Spin/add a new component to replace the faulty component

### System Metrics Description Example
* AVAILCPU percentage of free CPU cycles 
* FREEMEM available memory 
* PAGEIN/OUT virtual page in/out rate 
* MYFREEDISK free disk space 
* LOAD1 load in last 1 minute 
* LOAD5 load in last 5 minutes 

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

##### Notes:
* Private key to access NAT : 724_keypair.pem
* Ensure NatS3Access IAM role is created before running this template
* HTM instance uses a pre-baked AMI
* The aggregation is performed in the NAT instance and need to be manually started when workload is being simulated.
* References: 
    * [Optimizing CFN templates](https://aws.amazon.com/blogs/devops/optimize-aws-cloudformation-templates/)
    * [LAMP stack installation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-LAMP.html)