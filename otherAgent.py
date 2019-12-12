import pika
import json

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='to-agents')

while True:
	message = input('> ')
	jsonMessage = json.dumps({'sender': 'Celia', 'transcript': message, 'addressee': 'MarketPlace', 'currentState': 'abcdefg'})
	channel.basic_publish(exchange='', routing_key='to-agents', body=jsonMessage)
	print(" [x] Sent '" + message + "'")
connection.close()