#!/usr/bin/env python
import sys
import RPi.GPIO as GPIO
import lib.SimpleMFRC522 #Credit to 
from lib.doorController import DoorController
from flask import Flask
from flask import request
from multiprocessing import Process
from time import sleep
mustStop = 0;
app = Flask(__name__)
doorCtrl = DoorController(__name__)

# ==== Flask definitions ====
@app.route("/")
def index():
    return "200"
    
@app.route("/isNodeFree")
def isNodeFree():
	if doorCtrl.masterUrl == '':
		return "200" #Available for adoption
	else:
		return "409" #Conflict
    
@app.route('/adopt', methods=['POST'])
def adopt():
	global doorCtrl
	if doorCtrl.masterUrl == '':
		if request.method == 'POST':
			newMaster = request.form.get('master')
			print 'Received ' + newMaster
			if newMaster!= '':
				doorCtrl.setMaster(newMaster)
				return "202" #Accepted
			else:
				return "204" #No content
		else:
			return "405" #Method not allowed
	else:
		return "403" #Forbidden
			
			
@app.route('/adopt', methods=['GET'])
def getMaster():
	global doorCtrl
	if request.method == 'GET':
		return doorCtrl.masterUrl

# ===========================
# 		Threads declarations
# ===========================

def startWebServer():
	print "Start web server..."
	global app
	app.run(host='0.0.0.0')
	print "Web server stopped"

def startReadingLoop():
	try:
		global doorBerry
		reader = SimpleMFRC522.SimpleMFRC522()
		print "Starting reader..."
		while mustStop == 0 :
			id, text = reader.read()
			doorCtrl.validateCredential(id, text);
			print(id)
			print(text)
	except KeyboardInterrupt:
		pass		
	finally:
		print "Reader stopped"
		GPIO.cleanup()


# ===========================
# 		Starting up
# ===========================
#Delcare processes
webServerThread = Process(target=startWebServer)
rfidReaderThread = Process(target=startReadingLoop)
#Start processes
rfidReaderThread.start();
webServerThread.start();

try:
	while mustStop == 0 :
		sleep(0.3)
except KeyboardInterrupt:
	pass

# ===========================
# 		Shutting down
# ===========================
print "Shutting down"

#Notify threads
mustStop = 1
print "Notify threads to stop..."
sleep(1)
#Send terminate exception
webServerThread.terminate()
rfidReaderThread.terminate()
#Join threads
webServerThread.join()
rfidReaderThread.join()

#Cleanup GPIO handles
GPIO.cleanup()

print "Gracefully closed"
sleep(1)
