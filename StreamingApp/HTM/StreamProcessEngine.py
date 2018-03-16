'''
Created on Mar 11, 2018

@author: pratik
'''
import sys
import os  
os.environ['PYSPARK_SUBMIT_ARGS'] = r'--jars spark-streaming-kafka-0-8-assembly_2.11-2.3.0.jar StreamProcessEngine.py '+sys.argv[1]  

from PlainModel import Model

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils


class StreamApp:
    
    def runModel(self, model, data):
        self.count = self.count+1
        model.run(data, self.count)
            
    def streamProcessing(self):
        sc = SparkContext(master="local[*]", appName="PythonSparkStreamingKafka")
        sc.setLogLevel("OFF")
        ssc = StreamingContext(sc,5)
        model = Model()
        self.count = 0;
        self.ZK_quorum = sys.argv[1]+':2181'
        self.consumer_group_id = 'spark-streaming'
    
        """
        kafkaStream = KafkaUtils.createStream(streamingContext, \
            [ZK quorum], [consumer group id], [per-topic number of Kafka partitions to consume])
        """
        
        kafkaStream = KafkaUtils.createStream(ssc, self.ZK_quorum, self.consumer_group_id, {'cpu_metric':1})
        lines = kafkaStream.map(lambda x: x[1])
        #//lines.foreachRDD(func)
        lines.foreachRDD(lambda rdd: rdd.foreach( lambda data: self.runModel(model, data)))
        
        ssc.start()  
        ssc.awaitTermination()
        
        
if __name__ == '__main__':
    StreamApp().streamProcessing()
    
    