# ==========================================
# Title:  Multi-Product Negotiation AI
# Author: Johnathan Stadler
# Author: Jonathan Koppelman
# Date:   12 Dec 2019
# ==========================================

import pika
import json
from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import numpy as np
import math as m
from word2number import w2n
import sys

## Classify shoppers based on different types
## Preference illicitation

SENDER = sys.argv[1]
print("Staring agent", SENDER)

####
###  Products
##

products = ['egg', 'flour', 'sugar', 'milk', 'chocolate', 'blueberry', 'vanilla']
productPlurals = ['eggs', 'flours', 'sugars', 'milks', 'chocolates', 'blueberries', 'vanillas']
productUnits = {'egg':'eggs', 'flour':'cups of flour', 'sugar':'cups of sugar', 'milk':'cups of milk', 'chocolate':'ounces of chocolate', 'blueberry':'packets of blueberry', 'vanilla':'teaspoons of vanilla'}

####
###  Recipes
##

recipe_cake = {'egg':2,'flour':2,'milk':1,'sugar':1}
recipe_pancake = {'egg':1,'flour':2,'milk':2}

####
###  Responses
##


SOLD_PRODUCTS = []

start_conversation = [
	"Hello, I'm " + SENDER + ", what can I get for you?"
]

shit_talk_their_agent = [
	"Their products are not as high quality as ours."
]

brag_our_agent = [
	"Our products are much higher quality than theirs."
]

def lowerPrice(priceEngine):
	ret = "I can give you "
	for product, quantity in priceEngine.quantity.items():
		if quantity > 0:
			ret += str(quantity) + " " + productUnits[product] + ", "
	ret += "for $" + str(priceEngine.currentPrice)
	return ret

def otherAgentPoorOffer(priceEngine):
	ret = "There is no way they can be selling quality products at that price, or they would go out of business in a week. We on the other hand sell quality products at a reasonable price. That being said, I can still offer you  "
	for product, quantity in priceEngine.quantity.items():
		if quantity > 0:
			ret += str(quantity) + " " + str(product) + ", "
	ret += "for $" + str(priceEngine.currentPrice)
	return ret

talk_about_product = [
	"We offer only the highest quality products. We have eggs, flour, sugar, milk, chocolate, blueberry, and vanilla."
]

accepts_sale = [
	"I'm glad you chose to buy!",
	"I'm sure you will be happy with you purchase!",
	"Great, glad we could make a deal!"
]

####
###  Watson Setup
##

authenticator = IAMAuthenticator('6-M3Q9MtHGUnrMbqr_pQyZbozihUh27aP6CXPg3lPkZS')
assistant = AssistantV2(
    version='2018-09-20',
    authenticator=authenticator)
assistant.set_service_url('https://gateway.watsonplatform.net/assistant/api')

session = assistant.create_session("5a8c84ec-804f-4109-b8ef-ba58a8e7f7e3").get_result()
sessionID = eval(json.dumps(session, indent=2))['session_id']

### Intents: other agent
# lower-price...
# extra-offer..
# quality-description
# offers-products...

### Classes: marketplace
# start-conversation...
# asks-for-product...
# asks-about-product...
# accepts-sale...
# asks-for-lower-price..

####
###	 RabbitMQ Setup
##

# connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
connection = pika.BlockingConnection(pika.ConnectionParameters(host='128.113.21.86'))
channel1 = connection.channel()
channel1.queue_declare(queue='to-agents')
channel1.exchange_declare(exchange='amq.topic', exchange_type='topic', durable=True)
channel1.queue_bind(exchange='amq.topic', queue='to-agents')
if SENDER == 'Watson':
	channel1.queue_declare(queue='to-watson')
	channel1.exchange_declare(exchange='amq.topic', exchange_type='topic', durable=True)
	channel1.queue_bind(exchange='amq.topic', queue='to-watson')
else:
	channel1.queue_declare(queue='to-celia')
	channel1.exchange_declare(exchange='amq.topic', exchange_type='topic', durable=True)
	channel1.queue_bind(exchange='amq.topic', queue='to-celia')

channel1.queue_declare(queue='offers')
channel1.exchange_declare(exchange='amq.topic', exchange_type='topic', durable=True)
channel1.queue_bind(exchange='amq.topic', queue='offers')

channel2 = connection.channel()
channel2.queue_declare(queue='output-gate')
channel2.exchange_declare(exchange='amq.topic', exchange_type='topic', durable=True)
channel2.queue_bind(exchange='amq.topic', queue='output-gate')

class PriceEngine:
	cost = {}
	quantity = {}
	currentPrice = 0

	def __init__(self, utilities):
		global products
		for product in products:
			self.cost[product] = utilities[product]['parameters']['unitcost']
			self.quantity[product] = 0

	def getCost(self, product):
		return self.cost[product]

	def updateQuantity(self, product, num, increase):
		if increase:
			currentNum = self.quantity[product]
			if num > currentNum:
				self.currentPrice += np.around(4.5 * (num - currentNum) * self.cost[product], 2)
		self.quantity[product] = num

	def getUtility(self):
		global products
		utility = self.currentPrice
		for product in products:
			utility -= self.cost[product] * self.quantity[product]
		return utility

	def getFloorPrice(self):
		global products
		# TODO: Change this to the minimum amount we want to make on a product
		floorPrice = 0
		for product in products:
			floorPrice += self.cost[product] * self.quantity[product]
		return floorPrice

	def updatePrice(self, newPrice):
		self.currentPrice = newPrice

	def reset(self):
		self.currentPrice = 0
		self.quantity = {}
		for product in products:
			self.quantity[product] = 0

####
###  Agent Code
##

ROUND_STARTED = False
priceEngine = None
itr = 0

def isLabel(response, label):
	return label in response

def parseQuantitiesFromUser(string):
	global products, productPlurals
	try:
		quantity = {}
		for product in products:
			quantity[product] = None
		# Split text
		words = [word.strip(" ,.!?") for word in string.split(" ")]
		# Chnage word numbers to numers ex. 'two' to '2'
		for i in range(len(words)):
			try:
				num = w2n.word_to_num(words[i])
				words[i] = str(num)
			except ValueError:
				pass
		# Remove words except products and quantities
		words = [word for word in words if (word in products) or (word in productPlurals) or (word.isnumeric())]
		# Replace plural products with signular products
		for i in range(len(words)):
			if words[i] in productPlurals:
				words[i] = products[productPlurals.index(words[i])]
		# pair producs and quantites
		paired = list(zip(words[0::2], words[1::2]))
		# populate map
		for pair in paired:
			quantity[pair[1]] = int(pair[0])
		return quantity
	except Exception:
		print("Unable to parse string " + str(string))
		return

def reset():
	global itr, priceEngine
	itr = 0
	priceEngine.reset()

def hardReset():
	global itr, priceEngine, SOLD_PRODUCTS
	SOLD_PRODUCTS = []
	itr = 0
	priceEngine = None

# Receive message
def callback(ch, method, properties, body):
	global itr, priceEngine, SENDER, ROUND_STARTED, SOLD_PRODUCTS
	try:
		# update the turn number
		itr += 1

		body = json.loads(body)

		# set the utility from the initial message
		if 'msgType' in body.keys() and body['msgType'] == 'setAgentUtility':
			priceEngine = PriceEngine(body['utilityParameters']['utility'])
			transcript = str(priceEngine.cost)
			print(" [u] Received " + transcript + " utilities")
			return

		# Start the round
		if 'msgType' in body.keys() and body['msgType'] == 'startRound':
			ROUND_STARTED = True
			print(" [s] Received round start")
			return

		# End the round
		if 'msgType' in body.keys() and body['msgType'] == 'endRound':
			ROUND_STARTED = False
			hardReset()
			print(" [s] Received round end")
			return

		# The agent acceps an offer, so we want to start from scratch
		if 'msgType' in body.keys() and body['msgType'] == 'confirm':
			SOLD_PRODUCTS = body['quantities'].keys()
			reset()
			print(" [a] Received offer confirmed")
			return

		# ignore messages if the round hasn't started
		if not ROUND_STARTED:
			print(" [ ] Received " + str(body) + ", discarding due to no active round")
			return


		transcript = body['transcript']
		state = body['currentState']

		# the message we received
		print(" [x] Received '" + transcript + "'")

		# Message for watson classification
		message = assistant.message(
		    "5a8c84ec-804f-4109-b8ef-ba58a8e7f7e3",
		    sessionID,
		    input={'text': transcript},
		    context={
		        'metadata': {
		            'deployment': 'myDeployment'
		        }
		    }).get_result()

		# The classification of the message
		response = eval(json.dumps(message, indent=2))['output']['generic'][0]['text']
		print(" [c] Clasified as '" + response + "'")

		# Our current price
		ourCurrentPrice = priceEngine.currentPrice

		# respond based on the message classification
		if(isLabel(response,'agent-lower-price')):
			# update the current lowest offered price
			priceEngine.updatePrice(float(response.split(',')[-1].strip()))

		if(isLabel(response,'agent-offer-products')):
			# update the quantities based on what the other agent offered
			# TODO: We should decide if we are going to offer the same products as the other agent, or maybe offer different ones
			priceEngine.updatePrice(float(response.split(',')[-1].strip()))
			for product, quantity in parseQuantitiesFromUser(transcript).items():
				if  quantity is not None:
					priceEngine.updateQuantity(product, quantity, False)
		
		if(isLabel(response,'asks-for-products')):
			# update the quantities based on what the user asks for
			# print(parseQuantitiesFromUser(transcript))
			for product, quantity in parseQuantitiesFromUser(transcript).items():
				if quantity is not None:
					priceEngine.updateQuantity(product, quantity, True)

		if isLabel(response, 'start-conversation'):
			if not SENDER.lower() in transcript.lower():
				return
			message = start_conversation[0]
			jsonMessage = json.dumps({'sender': SENDER, 'transcript': message, 'room': 101, 'inReplyTo': state})
			channel2.basic_publish(exchange='amq.topic', routing_key='output-gate', body=jsonMessage)
			print(" [x] Sent '" + message + "'")
		elif isLabel(response, 'asks-about-product'):
			# TODO: figure out if they are asking about a specific product, or our products in general. Respond with a message about the product(s)
			if not SENDER.lower() in transcript.lower():
				return
			message = talk_about_product[0]
			jsonMessage = json.dumps({'sender': SENDER, 'transcript': message, 'room': 101, 'inReplyTo': state})
			channel2.basic_publish(exchange='amq.topic', routing_key='output-gate', body=jsonMessage)
			print(" [x] Sent '" + message + "'")
		elif isLabel(response, 'anything-else'):
			pass
		elif isLabel(response, 'accepts-sale'):
			# The other agent can't buy our product
			if not SENDER.lower() in transcript.lower():
				return
			message = accepts_sale[np.random.randint(len(accepts_sale))]
			jsonMessage = json.dumps({'sender': SENDER, 'transcript': message, 'room': 101, 'inReplyTo': state})
			channel2.basic_publish(exchange='amq.topic', routing_key='output-gate', body=jsonMessage)
			print(" [x] Sent '" + message + "'")
		else:
			lowerAmtRemaining = priceEngine.getUtility()

			# # decision making and theta calculation
			heuristic = (isLabel(response, 'agent-offer-products') * (-itr + lowerAmtRemaining * itr) + isLabel(response, 'agent-offer-products') * (lowerAmtRemaining *itr) + 
				(isLabel(response, 'shit-talk-our-agent') + isLabel(response, 'brag-their-agent') + isLabel(response, 'agent-extra-offer')) * (-itr + lowerAmtRemaining * itr)) + np.log(lowerAmtRemaining)

			theta = m.exp(heuristic)/(1+m.exp(heuristic))

			print(" [t] " + str(theta))

			# # response logic
			if theta < .5 or np.isnan(theta):
				if priceEngine.getUtility() < -1 and not SENDER.lower() in transcript.lower():
					# stay with ours and trash talk their quality/business sense
					pUpdate = np.around(ourCurrentPrice, 2)
					priceEngine.updatePrice(pUpdate)
					message = otherAgentPoorOffer(priceEngine)
					jsonMessage = json.dumps({'sender': SENDER, 'transcript': message, 'room': 101, 'inReplyTo': state})
					channel2.basic_publish(exchange='amq.topic', routing_key='output-gate', body=jsonMessage)
					print(" [x] Sent '" + message + "'")
				else:
					#their utility (according to us) is good, win back sale add more options
					#TODO: Fix the responses to make sense like, I can offer you the 3 eggs with an additional 2 sugars for _$
					pUpdate = np.around(ourCurrentPrice, 2)
					priceEngine.updatePrice(pUpdate)
					cakeCount = 0
					pancakeCount = 0
					for ingredient in priceEngine.quantity.keys():
						if ingredient in recipe_cake.keys() and (priceEngine.quantity[ingredient] > 0 or ingredient in SOLD_PRODUCTS):
							cakeCount += 1
						if ingredient in recipe_pancake.keys() and(priceEngine.quantity[ingredient] > 0 or ingredient in SOLD_PRODUCTS):
							pancakeCount += 1

					if cakeCount == pancakeCount:
						# here we are offering flavor because we don't now what they want
						flavors = ['chocolate', 'blueberry', 'vanilla']
						priceEngine.updateQuantity(flavors[np.random.randint(0,len(flavors))], 2, True)
						message = lowerPrice(priceEngine)
					else:
						if pancakeCount > cakeCount:
							rets = []
							for ing in recipe_pancake.keys():
								if priceEngine.quantity[ing] == 0:
									rets.append(ing)
							priceEngine.updateQuantity(rets[np.random.randint(0,len(rets))], 2, True)
							message = lowerPrice(priceEngine)
						else:
							rets = []
							for ing in recipe_cake.keys():
								if priceEngine.quantity[ing] == 0:
									rets.append(ing)
							priceEngine.updateQuantity(rets[np.random.randint(0,len(rets))], 2, True)
							message = lowerPrice(priceEngine)
					jsonMessage = json.dumps({'sender': SENDER, 'transcript': message, 'room': 101, 'inReplyTo': state})
					channel2.basic_publish(exchange='amq.topic', routing_key='output-gate', body=jsonMessage)
					print(" [x] Sent '" + message + "'")
					 					
			else:
				# lowerPrice
				floorPrice = priceEngine.getFloorPrice()
				currentPrice = priceEngine.currentPrice
				priceHack = np.log(currentPrice)
				offerPrice = currentPrice
				if priceHack<=lowerAmtRemaining:
					if priceHack<.50:
						offerPrice = floorPrice
					else:
						offerPrice = currentPrice - priceHack
				else:
					if lowerAmtRemaining == 0:
						# shit talk ERROR CONTROL (slips into lowerprice due to heurisitic messing up when there is no more price to lower)
						# shit-talk or brag or extra
						category = shit_talk_their_agent + brag_our_agent
						message = category[np.random.randint(len(category))]
						if message in give_extra_offer: give_extra_offer.remove(message)
						jsonMessage = json.dumps({'sender': SENDER, 'transcript': message, 'room': 101, 'inReplyTo': state})
						channel2.basic_publish(exchange='amq.topic', routing_key='output-gate', body=jsonMessage)
						print(" [x] Sent '" + message + "'")
					else:
						offerPrice = floorPrice

				offerPrice = np.around(offerPrice, 2)
				priceEngine.updatePrice(offerPrice)
				message = lowerPrice(priceEngine)
				jsonMessage = json.dumps({'sender': SENDER, 'transcript': message, 'room': 101, 'inReplyTo': state})
				channel2.basic_publish(exchange='amq.topic', routing_key='output-gate', body=jsonMessage)
				print(" [x] Sent '" + message + "'")
	except Exception:
		return

channel1.basic_consume(queue='to-agents', on_message_callback=callback, auto_ack=True)
if SENDER == 'Watson':
	channel1.basic_consume(queue='to-watson', on_message_callback=callback, auto_ack=True)
else:
	channel1.basic_consume(queue='to-celia', on_message_callback=callback, auto_ack=True)
channel1.basic_consume(queue='offers', on_message_callback=callback, auto_ack=True)

print(' [*] Waiting for messages. To exit press CTRL+C')
channel1.start_consuming()