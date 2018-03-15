'''
Created on Mar 11, 2018

@author: pratik
'''

import os  
os.environ['PYSPARK_SUBMIT_ARGS'] = r'--jars spark-streaming-kafka-0-8-assembly_2.11-2.3.0.jar StreamProcessEngine.py'  

from PlainModel import Model

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils


class StreamApp:
    
    def runModel(self, model, data):
        model.run(data)
            
    def streamProcessing(self):
        sc = SparkContext(master="local[*]", appName="PythonSparkStreamingKafka")
        sc.setLogLevel("OFF")
        ssc = StreamingContext(sc,5)
        model = Model()
        
        """
        kafkaStream = KafkaUtils.createStream(streamingContext, \
            [ZK quorum], [consumer group id], [per-topic number of Kafka partitions to consume])
        """
        
        kafkaStream = KafkaUtils.createStream(ssc, 'ec2-18-219-238-85.us-east-2.compute.amazonaws.com:2181', 'spark-streaming', {'cpu_metric':1})
        lines = kafkaStream.map(lambda x: x[1])
        #//lines.foreachRDD(func)
        lines.foreachRDD(lambda rdd: rdd.foreach( lambda data: self.runModel(model, data)))
        
        ssc.start()  
        ssc.awaitTermination()
        
        
if __name__ == '__main__':
    StreamApp().streamProcessing()
    
    