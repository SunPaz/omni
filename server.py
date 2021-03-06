#!/usr/bin/env python3
"""
This script launch the server, used as a master to handle
clients configuration and validate credentials.

It can be run on any platform with python and pip requierments installed
"""
__version__ = '0.1'

"""  """
from configparser import ConfigParser
import json
import time
from threading import Thread

""" Flask imports """
from flask import Flask, request, send_from_directory, render_template, jsonify, request, Blueprint
from web.router import query_js, query_styles, view_index, edp_is_alive, edp_confirm_adopt, view_access_management

""" Business import """
from lib.datasource import DataSource
from lib.visibilityManager import VisibilityManager
from lib.common import ServerSetting, DeviceConfiguration, Member, DeviceStatus, PrintColor

""" When called by external WSGI server """
if __name__ == "__main__":
    CONNECTION_FILE_PATH = "./cfg/connectionString.sql" #Default
else:
    CONNECTION_FILE_PATH = "/app/omni/cfg/connectionString.sql" #Default

SERVER_SECRET = "DaSecretVectorUsedToHashCommunication" #Default
connected_devices = []
app = Flask(__name__, static_url_path='')
start_time = time.time()

""" Loading static routing blueprints (static pages, ressources queries) """
app.register_blueprint(query_js)
app.register_blueprint(query_styles)
app.register_blueprint(view_index)
app.register_blueprint(edp_confirm_adopt)
app.register_blueprint(edp_is_alive)
app.register_blueprint(view_access_management)

""" Flask routing definition """
""" TODO : Put everything in the "router.py" file """

#View state
@app.route("/stateView")
def view_state():
	return render_template('./server/system/stateView.html', devices=connected_devices, uptime=get_uptime())

#View enroll
@app.route("/enrollView")
def view_enroll():
	""" Check devices and load settings """
	source = DataSource(DataSource.TYPE_DATABASE, CONNECTION_FILE_PATH)
	settingAccess = ServerSetting('enroll')
	settingAccess.parameters = source.get_not_enrolled_members()
	settingAccess.groups = source.get_members_groups()
	settings = []
	settings.append(settingAccess)
	return render_template('./server/accessManagement/enrollView.html', settings=settings)

#View group
@app.route("/groupView")
def view_groups():
	return render_template('./server/accessManagement/groupView.html')

#View settings
@app.route("/settingsView")
def view_settings():
	""" Check devices and load settings """
	source = DataSource(DataSource.TYPE_DATABASE, CONNECTION_FILE_PATH)
	""" TODO : Return settings according to devices types """
	settingAccess = ServerSetting('enroll')

	settings = []
	settings.append(settingAccess)

	return render_template('./server/common/settingsView.html', settings=settings)

@app.route("/enroll", methods=['POST'])
def enroll():
	member = Member(request.form['Id'])
	member.lastname = request.form['lastname']
	member.firstname = request.form['firstname']
	member.groupId = request.form['groupId']

	source = DataSource(DataSource.TYPE_DATABASE, CONNECTION_FILE_PATH)
	source.update_member_info(member)

	return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

@app.route("/report/state", methods=['POST'])
def report_state():
	data = request.data
	device_status_data = json.loads(data)
	for x in connected_devices:
		if x.client_id == device_status_data['client_id']:
			x.is_in_error = device_status_data['is_in_error']
			x.error_status = device_status_data['error_status']
			break
	return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

@app.route("/accessRule/<zone>/token/<credential>", methods=['GET'])
def validate_credential(zone, credential):
	"""
	Token is already calculated
	"""
	source = DataSource(DataSource.TYPE_DATABASE, CONNECTION_FILE_PATH)

	canAccess = source.get_or_create_client_access_rights(credential, zone)

	if canAccess:
		return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
	else:
		return json.dumps({'success':False}), 403, {'ContentType':'application/json'}

@app.route("/accessRule/<zone>/<token_type>/token_data", methods=['POST'])
def report_state_zone(zone, token_type):
	data = request.data
	data = json.loads(data)

	if token_type == 'characteristics':
		print(str(data))
	else:
		return json.dumps({'success':False}), 404, {'ContentType':'application/json'}

	return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

@app.route("/configuration/<client_id>")
def configuration(client_id):
	configuration = get_configuration_by_client_id(client_id)
	configuration.secret = SERVER_SECRET
	""" Update client endpoint """
	for x in connected_devices:
		if x.client_id == client_id:
			x.endpoint = str(request.remote_addr)
			break

	if configuration is None:
		return json.dumps({'success':False}), 204, {'ContentType':'application/json'}

	print(PrintColor.OKBLUE + "Sending configuration for client " + str(client_id))
	return jsonify(configuration.serialize()), 200, {'ContentType':'application/json'}

def get_configuration_by_client_id(client_id):
	source = DataSource(DataSource.TYPE_DATABASE, CONNECTION_FILE_PATH)
	conf = source.load_device_configuration(client_id)

	""" Update list """
	for x in connected_devices:
		if x.client_id == client_id:
			connected_devices.remove(x)
			break

	connected_devices.append(conf)

	return conf

def get_uptime():
	from datetime import timedelta
	uptime_string = str(timedelta(seconds = time.time() - start_time))

	return uptime_string

def load_server_configuration():
	source = DataSource(DataSource.TYPE_DATABASE, CONNECTION_FILE_PATH)
	conf = source.load_server_configuration()

def pre_start_diagnose():
	print(PrintColor.OKBLUE + "Pre-start diagnostic ...")
	print(PrintColor.OKBLUE + "1) Loading application configuration ...")

	""" Reading configuration """
	appConfig = ConfigParser()
	appConfig.read('./cfg/config.ini')

	print(PrintColor.OKBLUE + "Sections found : " + str(appConfig.sections()))

	if len(appConfig.sections()) == 0:
		raise RuntimeError(PrintColor.WARNING + "Could not open configuration file")

	CONNECTION_FILE_PATH = appConfig.get("AppConstants", "ConnectionStringFilePath")
	SERVER_SECRET = appConfig.get("AppConstants", "Secret")

	print(PrintColor.OKBLUE + " >> Configuration OK")

	print(PrintColor.OKBLUE + "2) Trying to reach datasource...")
	sourceDbConnection = DataSource(DataSource.TYPE_DATABASE, CONNECTION_FILE_PATH)
	dataSourceOk = sourceDbConnection.is_reachable()
	if dataSourceOk == 1:
		print(PrintColor.OKBLUE + " >> Datasource OK")
	else:
		print(PrintColor.WARNING + " >> Datasource unreachable.")


#Only if it's run
if __name__ == "__main__":
	pre_start_diagnose()

	""" Start discovery manager """
	visibility_manager = VisibilityManager()
	discovery_thread = Thread(target=visibility_manager.listen_for_discovery_datagram)

	discovery_thread.start()

	print(PrintColor.OKGREEN + "Start web server...")
	app.run(host='0.0.0.0', port=5000)
	print(PrintColor.OKGREEN + "Web server stopped.")
	visibility_manager.must_stop = True
	print(PrintColor.OKBLUE + "Waiting for secondaries threads")
	discovery_thread.join()
