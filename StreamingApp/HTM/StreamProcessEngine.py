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
    
    def utilMapFunc(self, time, rdd):
        taken = rdd.take(1)
        print("-------------------------------------------")
        print("Time: %s" % time)
        print("-------------------------------------------")
        for record in taken[:10]:
            print(record)
            self.model.run(record)    
        if len(taken) > 10:
            print("...")
        print("")
    
        
    def streamProcessing(self):
        sc = SparkContext(master="local[*]", appName="PythonSparkStreamingKafka")
        sc.setLogLevel("WARN")
        ssc = StreamingContext(sc,10)
        
        """
        kafkaStream = KafkaUtils.createStream(streamingContext, \
            [ZK quorum], [consumer group id], [per-topic number of Kafka partitions to consume])
        """
        
        kafkaStream = KafkaUtils.createStream(ssc, 'ec2-18-216-14-9.us-east-2.compute.amazonaws.com:2181', 'spark-streaming', {'cpu_metric':1})
        lines = kafkaStream.map(lambda x: x[1])
        #//lines.foreachRDD(func)
        #model.run(lines)    
        lines.foreachRDD(self.utilMapFunc)
        
        ssc.start()  
        ssc.awaitTermination()
        
        
if __name__ == '__main__':
    streamApp = StreamApp()
    streamApp.model = Model()
    streamApp.streamProcessing()
    
    