import pika
import json

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='to-watson')

message = eval('{ "msgType": "endRound", "timestamp": "<time>" }')
jsonMessage = json.dumps(message)
channel.basic_publish(exchange='', routing_key='to-watson', body=jsonMessage)
print(" [x] Sent end round utilities")
connection.close()