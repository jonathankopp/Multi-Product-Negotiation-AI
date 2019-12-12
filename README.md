Multi-Product Negotiation:

This project contains the following files:
	agent.py           - The main agent code
	sendUtilities.py   - File to send fixed utilities for testing
	startRound.py      - File to send a start round message
	marketPlace.py     - Waits for input and sends it from the market place
	otherAgent.py      - Waits for input and sends it from the other agent
	endRound.py        - File to send an end round message
	output.py          - Listen and print agent responses

To run locally:
Make sure the MQTT (pika) connection is listening on localhost (CTRL-F 'connection' to find the code block)
	1- "python3 agent.py [Watson or Celia]"
	2- "python3 sendUtilities.py" (to send utilities)
	3- "python3 startRound.py" (to start round)
	4- use "python3 marketPlace.py" and "python3 otherAgent.py" to send messages
	5- "python3 endRound.py"
	6- Repeat from step 2 to run another round


To run in CISL:
	1- In agent.py comment out local host line and uncomment line with ip, and put in correct ip
	2- "python3 agent.py [Watson or Celia]"

The agent.py code uses the following packages that need to be installed with pip:
	1- pika
	2- ibm_watson
	3- ibm_watson_developer
	4- numpy
	5- word2number

RabbitMQ must be installed and running to run any file in the project