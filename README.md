![Real-time anomaly prediction in distributed systems](https://github.com/gitPratikSingh/Real-time-anomaly-prediction-in-distributed-systems/blob/master/Capture.PNG?raw=true "Real-time anomaly prediction in distributed systems")


![Model Architectures]
https://github.com/gitPratikSingh/Real-time-anomaly-prediction-in-distributed-systems/blob/master/ModelArchitecture.jpg

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

	
###Challenges/Questions  :

Operational data traces from cloud environment
* Start from scratch? Can we use the existing implementations and build on top of that ? 
* Causes of anomaly can be resource contention/software bugs/hardware failures..etc Are we supposed to detect anomaly for all?
* Can we limit the anomalies to one type to begin with and later expand on that to a more generalized anomaly detection? How to model anomalies? 
* Is the target hypervisor or should we work at a higher layer of abstraction?

* Should our prediction algorithm exhibit different level of sensitivity to different type of data..Eg. CPU data vs Memory data.!.. (Yes!)

* For, large clusters we will have large volume of continuously monitored data with high velocity(depends on the sampling interval), 
which can make it difficult for real time diagnosis. 

* Running the detection tool can take up resources of the system. We could keep the detection tool lightweight and draw the data to another node(s) for indexing and processing. Something like ELK for log/metrics collection??

* We should not do the prediction on the same cluster, as any cluster component can go down.Instead we can use another vendor’s cluster to perform prediction. This will need us to send batches of monitored data and getting back the predictions.

* The online prediction model will detect component faults… but how to do fault localization??? (Causality graph vs Earliest manifestation time) How to get earliest manifestation time in a distributed system as there is no synchronous clock? 

* How to distinguish workload change and anomaly? Clearly define an anomaly?? What would it constitute of? 

* How should anomaly be handled?? Mechanisms differ for type of anomaly -

Anomaly type		Causes		Measures	hardware	malfunction	Replace HW resource on cloud 


glitch				Should we wait to see a pattern or immediately take action? Tradeoff between response time vs optimality
software
Configuration fault
Network fault


How to detect that?? Based on log messages?
Reconfigure to fix?


bug
Find patches? Raise tickets (human intervention req)



### My ideas
* Adaptive frequency of data collection. Eg. 5 sec under normal circumstances and if alert situation happens then sampling every 1s or less? 
* Frequency scaling?


###Topics that we need to work on

* KVM vs XEN ? https://www.linux.com/news/kvm-or-xen-choosing-virtualization-platform


* Time series analysis techniques (for anomaly detection)
	https://github.com/IrinaMax/CPU-usage-and-anomaly-detection, https://www.infoq.com/articles/deep-learning-time-series-anomaly-detection

* Which algorithm works best.. We can also choose to use ensemble models..decide
http://www-tandfonline-com.prox.lib.ncsu.edu/doi/abs/10.1080/07474938.2010.481556

* Our monitoring data set is un-labelled and might show spiky (noisy) and seasonal (rhythmic) characteristics from a multitude of different causes. These characteristics can mask or exaggerate behaviors. Consequently, we are interested in unsupervised anomaly detection techniques those should be independent of fixed limits and thresholds so that they can adapt to a live and evolving environment, but still be able to detect sudden changes and rhythm disturbances.


* Most virtualization platforms provide interfaces that allow the hypervisor (or domain 0 in the Xen platform [2]) to extract guest VM’s system-level metrics from outside. PREPARE uses libxenstat to monitor guest VM’s resource usage from domain 0. However, it is challenging to extract the memory usage information of guest VMs from outside in Xen since the memory utilization is only known to the OS within each guest VM. Thus, if we want to monitor the application’s memory usage metric, we need to install a simple memory monitoring daemon (e.g., through the /proc interface in Linux) within the guest VM to get the memory usage statistics

    

###Resources
* CloudScale: https://github.ncsu.edu/ssjoshi2/Cloud-Scale
* UBL: https://github.com/mahekchheda/UPrepare
* Chord: https://github.com/salilkanitkar/IP_P1_ChordLT, https://github.com/jerisalan/chordX

* Insightfinder Agent code: https://github.com/insightfinder/InsightAgent


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
                
