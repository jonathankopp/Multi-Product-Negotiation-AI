This project contains the following files:
agent.py- The main agent code
sendUtilities.py- File to send fixed utilities for testing
startRound.py- File to send a start round message
marketPlace.py- Waits for input and sends it from the market place
otherAgent.py- Waits for input and sends it from the other agent
endRound.py- File to send an end round message

To run locally:
Make sure the MQTT (pika) connection is listening on localhost (CTRL-F 'connection' to find the code block)
> python3 agent.py <Watson or Celia>
> python3 sendUtilities.py (to send utilities)
> python3 startRound.py (to start round)
use 'python3 marketPlace.py' and 'python3 otherAgent.py' to send messages
> python3 endRound.py


To run in CISL:
> python3 agent.py <Watson or Celia>

The agent.py code uses the following packages that need to be installed with pip:
pika
ibm_watson
ibm_watson_developer
numpy
word2number