![Real-time anomaly prediction in distributed systems](https://github.com/gitPratikSingh/Real-time-anomaly-prediction-in-distributed-systems/blob/master/Capture.PNG?raw=true "Real-time anomaly prediction in distributed systems")


![Model Architectures](https://github.com/gitPratikSingh/Real-time-anomaly-prediction-in-distributed-systems/blob/master/ModelArchitecture.jpg?raw=true "Model Architectures")

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
#### Cloudformation

* Create Stack : `python create_stack.py`
* Key to access clients : 724_keypair.pem
* Ensure NatS3Access IAM role is created before running this template
* References: 
    * [Optimizing CFN templates](https://aws.amazon.com/blogs/devops/optimize-aws-cloudformation-templates/)
    * [LAMP stack installation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-LAMP.html)
                
![AWS Architectures](https://github.com/atambol/Real-time-anomaly-prediction-in-distributed-systems/blob/master/AWS_Architecture.png?raw=true "AWS_Architectures")

#### RUBiS

* [RUBiS Repository](https://github.com/atambol/RUBiS)
* Current installation creates three instance for RUBiS: 
    * Rubis Client
    * DB Server
    * Web Server
* Rubis Web Server UI: http://<NAT's Public IP>:8080/PHP/index.html
