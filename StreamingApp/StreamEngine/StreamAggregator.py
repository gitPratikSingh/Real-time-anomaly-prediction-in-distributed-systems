from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka.errors import KafkaError

counter = 0
aggregate_size = 200
response_time = 0
bootstrap_servers='172.25.130.9:9092'
consumer_topic = 'rubis'
producer_topic = 'aggregated'
producer = KafkaProducer(bootstrap_servers=[bootstrap_servers])
consumer = KafkaConsumer(consumer_topic,
                         auto_offset_reset='earliest',
                         bootstrap_servers=[bootstrap_servers])

while True:
    for message in consumer:
        counter += 1
        try:
            response_time += int(message.value)
        except ValueError as err:
            print err
        if counter == aggregate_size:
            response_time /= aggregate_size
            future = producer.send(producer_topic, response_time)
            counter = 0
            response_time = 0
            # Block for 'synchronous' sends
            try:
                record_metadata = future.get(timeout=10)
            except KafkaError as err:
                print err