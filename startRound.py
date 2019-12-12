import pika
import json

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='to-watson')

message = eval('{ "msgType": "startRound", "roundNumber": 1, "roundDuration": 600, "timestamp": "<time>" }')
jsonMessage = json.dumps(message)
channel.basic_publish(exchange='', routing_key='to-watson', body=jsonMessage)
print(" [x] Sent start round utilities")
connection.close()