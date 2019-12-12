import pika
import json

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='to-watson')

message = eval("{'sender': 'MarketPlace', 'msgType': 'setAgentUtility', 'utilityParameters': {'currencyUnit': 'USD', 'utility': {'egg': {'type': 'unitcost', 'unit': 'each', 'parameters': {'unitcost': 0.44 } }, 'flour': {'type': 'unitcost', 'unit': 'cup', 'parameters': {'unitcost': 0.53 } }, 'sugar': {'type': 'unitcost', 'unit': 'cup', 'parameters': {'unitcost': 0.63 } }, 'milk': {'type': 'unitcost', 'unit': 'cup', 'parameters': {'unitcost': 0.27 } }, 'chocolate': {'type': 'unitcost', 'unit': 'ounce', 'parameters': {'unitcost': 0.35 } }, 'blueberry': {'type': 'unitcost', 'unit': 'packet', 'parameters': {'unitcost': 0.28} }, 'vanilla': {'type': 'unitcost', 'unit': 'teaspoon', 'parameters': {'unitcost': 0.28 } } } } }")
jsonMessage = json.dumps(message)
channel.basic_publish(exchange='', routing_key='to-watson', body=jsonMessage)
print(" [x] Sent json utilities")
connection.close()