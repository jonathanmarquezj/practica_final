from apiclient.discovery import build
import pickle
import pprint

import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery

import os
import flask
import json

from datetime import date
from datetime import datetime

#Para eliminar el token cuando terminemos
from os import remove

app = flask.Flask(__name__)



#-------------------------------------------------------------------
#     WEB
#-------------------------------------------------------------------
"""

#INICIO
@app.route('/', methods=["GET", "POST"])
def inicio():
	return render_template("index.html")


#SELECCIONAR CALENDARIO
@app.route('/seleccionarCalendario', methods=["GET", "POST"])
def seleccionarCalendario():
	# Miramos si existe el token, en caso contrario tendremos que crearlo
	if os.path.exists("token.pkl"):
		return render_template("seleccionarCalendario.html", calendarios=listarCalendarios())
	else:
		crearToken()

		return render_template("seleccionarCalendario.html", calendarios=listarCalendarios())



#CALENDARIO
@app.route('/calendario', methods=["GET", "POST"])
@app.route('/calendario/<mensaje>', methods=["GET", "POST"])
@app.route('/calendario/<mensaje>/<calendar_id>', methods=["GET", "POST"])
def calendario(mensaje=None, calendar_id=None):
	# Miramos si a enviado el ID del calendario por post
	if request.method == "POST":
		calendar_id=request.form['calendar_id']
	# En el caso de que no tengamos el ID del calendario tanto por POST como por GET, lo mandamos a que lo seleccione
	if calendar_id==None and request.method != "POST":
		return redirect(url_for('seleccionarCalendario'))

	# Creamos el archivo "static/eventos.json" que sera donde estaran los eventos
	solicitarEventos(calendar_id)

	return render_template("calendario.html", mensaje=mensaje, calendar_id=calendar_id)




# AÑADIR EVENTO EN EL CALENDARIO
@app.route('/anadirEvento/<calendar_id>', methods=["GET", "POST"])
@app.route('/anadirEvento/<mensaje>/<calendar_id>', methods=["GET", "POST"])
def anadirEvento(calendar_id, mensaje=None):
	# Miramos si envio el formulario para insertar los datos
	if request.method == "POST":
		calendar_id=request.form['calendar_id']
		titulo=request.form['titulo']
		fechaInicio=request.form['fechaInicio']
		horaInicio=request.form['horaInicio']
		fechaFin=request.form['fechaFin']
		horaFin=request.form['horaFin']

		# Comprobamos la fecha
		if fechaInicio.replace('-','') > fechaFin.replace('-',''):
			# Si pone mal la fecha le ponemos un mensaje
			return redirect(url_for('anadirEvento', mensaje='Lo sentimos pero no se pudo insertar el evento. La fecha inicio no pueder ser mayor a la fecha fin', calendar_id=calendar_id))
		else:
			# Si todo es correcto metemos el evento y lo mandamos al calendario
			anadirEvento(titulo, fechaInicio, horaInicio, fechaFin, horaFin, calendar_id)
			# Le pedimos al calendario los eventos de nuevo 
			solicitarEventos(calendar_id)
			return redirect(url_for('calendario', mensaje='Evento insertado', calendar_id=calendar_id))

	else:
		return render_template("anadirEvento.html", mensaje=mensaje, calendar_id=calendar_id)


# MODIFICAR EVENTO EN EL CALENDARIO
@app.route('/modificarEvento/<id_evento>/<calendar_id>', methods=["GET", "POST"])
@app.route('/modificarEvento/<id_evento>/<calendar_id>/<mensaje>', methods=["GET", "POST"])
def modificarEvento(id_evento, calendar_id, mensaje=None):
	# Miramos si envio el formulario para insertar los datos
	if request.method == "POST":
		id_evento=request.form['id_evento']
		titulo=request.form['titulo']
		fechaInicio=request.form['fechaInicio']
		horaInicio=request.form['horaInicio']
		fechaFin=request.form['fechaFin']
		horaFin=request.form['horaFin']
		calendar_id=request.form['calendar_id']

		# Comprobamos la fecha
		if fechaInicio.replace('-','') > fechaFin.replace('-',''):
			# Si pone mal la fecha le ponemos un mensaje
			return redirect(url_for('modificarEvento', mensaje='Lo sentimos pero no se pudo insertar el evento. La fecha inicio no pueder ser mayor a la fecha fin', id_evento=id_evento, titulo=titulo, fechaInicio=fechaInicio, horaInicio=horaInicio, fechaFin=fechaFin, horaFin=horaFin, calendar_id=calendar_id))
		else:
			# Si todo es correcto metemos el evento y lo mandamos al calendario
			actualizarEvento(id_evento, titulo, fechaInicio, horaInicio, fechaFin, horaFin, calendar_id)
			# Le pedimos al calendario los eventos de nuevo
			solicitarEventos(calendar_id)
			return redirect(url_for('calendario', mensaje='Evento modificado', calendar_id=calendar_id))

	else:
		# Pedimos al calendario el evento con el id correspondiente y lo mostramos al usuario
		credentials = pickle.load(open("token.pkl", "rb"))
		service = build("calendar", "v3", credentials=credentials)

		event = service.events().get(calendarId=calendar_id, eventId=id_evento).execute()

		titulo=event['summary']
		if 'dateTime' in event['start']:
			fechaInicio=event['start']['dateTime'].split('T')[0]
			horaInicio=event['start']['dateTime'].split('T')[1][0:5]
		if 'date' in event['start']:
			fechaInicio=event['start']['date'].split('T')[0]
			horaInicio='00:00'

		if 'dateTime' in event['end']:
			fechaFin=event['end']['dateTime'].split('T')[0]
			horaFin=event['end']['dateTime'].split('T')[1][0:5]
		if 'date' in event['end']:
			fechaFin=event['end']['date'].split('T')[0]
			horaFin='00:00'


		return render_template("modificarEvento.html", id_evento=id_evento, mensaje=mensaje, titulo=titulo, fechaInicio=fechaInicio, horaInicio=horaInicio, fechaFin=fechaFin, horaFin=horaFin, calendar_id=calendar_id)

# Elimina el evento del calendario
@app.route('/eliminarEvento/<calendar_id>/<event_id>', methods=["GET", "POST"])
def eliminarEvento(calendar_id, event_id):
	eliminarEvento(calendar_id, event_id)
	return redirect(url_for('calendario', mensaje='Evento eliminado', calendar_id=calendar_id))

# Elimina el archivo Token que es el que tiene el acceso al calendario
@app.route('/eliminarToken', methods=["GET", "POST"])
def eliminarToken():
	remove("token.pkl")
	return render_template("index.html")

#PARA PERSONALIZAR EL ERROR 404
@app.errorhandler(404)
def page_not_found(error):
    return "<h1>ERROR: 404</h1><br/>página no encontrada <br/><br/><a href='/'>Atras</a>"






#-------------------------------------------------------------------
#     FUNCIONES PYTHON
#-------------------------------------------------------------------

# Devuelve una lista de todos los calendarios que tiene el usuario
def listarCalendarios():
	credentials = pickle.load(open("token.pkl", "rb"))
	service = build("calendar", "v3", credentials=credentials)
	result = service.calendarList().list().execute()

	calendarios = {}
	for calendar_list_entry in result['items']:
		calendarios[calendar_list_entry['id']] = calendar_list_entry['summary']

	return calendarios


# Actualiza el evento que el usuario a modificado
def actualizarEvento(evento_id, titulo, fechaInicio, horaInicio, fechaFin, horaFin, calendar_id, descripcion=None, localidad=None):
	# Creamos la pantilla del evento para despues mandarla a google
	timezone = 'Europe/Madrid'
	event = {
		'summary': titulo,
		'location': localidad,
		'description': descripcion,
		'start': {
			'dateTime': fechaInicio +"T"+ horaInicio +":00",
			'timeZone': timezone,
		},
		'end': {
			'dateTime': fechaFin+"T"+ horaFin +":00",
			'timeZone': timezone,
		},
		'reminders': {
			'useDefault': False,
			'overrides': [
				{'method': 'email', 'minutes': 24 * 60},
				{'method': 'popup', 'minutes': 10},
			],
		},
	}
	# Iniciamos el token
	credentials = pickle.load(open("token.pkl", "rb"))
	service = build("calendar", "v3", credentials=credentials)
	# Insertamos el evento
	service.events().update(calendarId=calendar_id, eventId=evento_id, body=event).execute()


# Añade el evento
def anadirEvento(titulo, fechaInicio, horaInicio, fechaFin, horaFin, calendar_id, descripcion=None, localidad=None):
	# Creamos la pantilla del evento para despues mandarla a google
	timezone = 'Europe/Madrid'
	event = {
		'summary': titulo,
		'location': localidad,
		'description': descripcion,
		'start': {
			'dateTime': fechaInicio +"T"+ horaInicio +":00",
			'timeZone': timezone,
		},
		'end': {
			'dateTime': fechaFin+"T"+ horaFin +":00",
			'timeZone': timezone,
		},
		'reminders': {
			'useDefault': False,
			'overrides': [
				{'method': 'email', 'minutes': 24 * 60},
				{'method': 'popup', 'minutes': 10},
			],
		},
	}
	# Iniciamos el token
	credentials = pickle.load(open("token.pkl", "rb"))
	service = build("calendar", "v3", credentials=credentials)
	# Insertamos el evento
	service.events().insert(calendarId=calendar_id, body=event).execute()


# Solicita al servidor todos los eventos del calendario
def solicitarEventos(calendar_id):
	credentials = pickle.load(open("token.pkl", "rb"))
	service = build("calendar", "v3", credentials=credentials)
	# Le decimos que el evento tiene que tener una fecha minima
	now = datetime.now()
	fechaMinima = format(now.year)+'-01-01T01:00:00.226752Z'
	# Le decimos un maximo de eventos para mostrar, puede ir de 1 a 2500
	eventosMaximos = 2500
	# Le pedimos que nos lo ordene
	ordenarPor = 'startTime'

	result = service.events().list(calendarId=calendar_id, timeMin=fechaMinima, maxResults=eventosMaximos, singleEvents=True, orderBy=ordenarPor).execute()

	events = result.get('items', [])

	# Empezamos a crear el archivo que sera el que contenga los eventos
	file = open("static/eventos.json", "w")
	file.write("[" + os.linesep)

	for event in events:
		file.write("	{" + os.linesep)
		file.write('		"title": "'+ event['summary'] +'",' + os.linesep)
		if 'dateTime' in event['start']:
			file.write('		"start": "'+ event['start']['dateTime'] +'",' + os.linesep)
		if 'date' in event['start']:
			file.write('		"start": "'+ event['start']['date'] +'",' + os.linesep)
		if 'dateTime' in event['end']:
			file.write('		"end": "'+ event['end']['dateTime'] +'",' + os.linesep)
		if 'date' in event['end']:
			file.write('		"end": "'+ event['end']['date'] +'",' + os.linesep)
		file.write('		"url": "/modificarEvento/'+ event['id']+'/'+ calendar_id +'"' + os.linesep)
		file.write("	}," + os.linesep)

	file.write("{}]")


# Elimina el evento
def eliminarEvento(calendar_id, event_id):
	credentials = pickle.load(open("token.pkl", "rb"))
	service = build("calendar", "v3", credentials=credentials)

	service.events().delete(calendarId=calendar_id, eventId=event_id).execute()


# Crea el token del calendario para que el usuario pueda acceder
def crearToken():

	# Solicitamos permiso para acceder al calendario del cliente.
	scopes = ['https://www.googleapis.com/auth/calendar']
	flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", scopes=scopes)
	# Redirigimos, a la web de google para dar permiso y guardamos el token en una variable
	credentials = flow.run_local_server(port=0)

	# Creamos el token en el servidor para no tener que solicitar de nuevo el permiso
	pickle.dump(credentials, open("token.pkl", "wb"))


# --------------------------------------

"""
#PRUEBA


CLIENT_SECRETS_FILE='client_secret_heroku.json'
SCOPES=['https://www.googleapis.com/auth/calendar']

app.secret_key = '6qdL7nEDswA88vdnx-WIUdJB'

API_SERVICE_NAME = 'calendar'
API_VERSION = 'v2'


@app.route('/')
def index():
	return print_index_table()


@app.route('/test')
def test_api_request():
	if 'credentials' not in flask.session:
		return flask.redirect('authorize')

	# Load credentials from the session.
	credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])

	drive = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
	files = drive.files().list().execute()

	# Save credentials back to session in case access token was refreshed.
	# ACTION ITEM: In a production app, you likely want to save these
	#              credentials in a persistent database instead.
	flask.session['credentials'] = credentials_to_dict(credentials)

	return flask.jsonify(**files)


@app.route('/authorize')
def authorize():
	# Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
	flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)

	# The URI created here must exactly match one of the authorized redirect URIs
	# for the OAuth 2.0 client, which you configured in the API Console. If this
	# value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
	# error.
	flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

	authorization_url, state = flow.authorization_url(access_type='offline',include_granted_scopes='true')

	# Store the state so the callback can verify the auth server response.
	flask.session['state'] = state

	return flask.redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
	# Specify the state when creating the flow in the callback so that it can
	# verified in the authorization server response.
	state = flask.session['state']

	flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
	flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

	# Use the authorization server's response to fetch the OAuth 2.0 tokens.
	authorization_response = flask.request.url
	flow.fetch_token(authorization_response=authorization_response)

	# Store credentials in the session.
	# ACTION ITEM: In a production app, you likely want to save these
	#              credentials in a persistent database instead.
	credentials = flow.credentials
	flask.session['credentials'] = credentials_to_dict(credentials)

	return flask.redirect(flask.url_for('test_api_request'))


@app.route('/revoke')
def revoke():
	if 'credentials' not in flask.session:
		return ('You need to <a href="/authorize">authorize</a> before ' + 'testing the code to revoke credentials.')

	credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])

	revoke = requests.post('https://oauth2.googleapis.com/revoke',params={'token': credentials.token},headers = {'content-type': 'application/x-www-form-urlencoded'})

	status_code = getattr(revoke, 'status_code')
	if status_code == 200:
		return('Credentials successfully revoked.' + print_index_table())
	else:
		return('An error occurred.' + print_index_table())


@app.route('/clear')
def clear_credentials():
	if 'credentials' in flask.session:
		del flask.session['credentials']
	return ('Credentials have been cleared.<br><br>' + print_index_table())


def credentials_to_dict(credentials):
	return {'token': credentials.token,
		'refresh_token': credentials.refresh_token,
		'token_uri': credentials.token_uri,
		'client_id': credentials.client_id,
		'client_secret': credentials.client_secret,
		'scopes': credentials.scopes}

def print_index_table():
	return ('<table>' +
		'<tr><td><a href="/test">Test an API request</a></td>' +
		'<td>Submit an API request and see a formatted JSON response. ' +
		'    Go through the authorization flow if there are no stored ' +
		'    credentials for the user.</td></tr>' +
		'<tr><td><a href="/authorize">Test the auth flow directly</a></td>' +
		'<td>Go directly to the authorization flow. If there are stored ' +
		'    credentials, you still might not be prompted to reauthorize ' +
		'    the application.</td></tr>' +
		'<tr><td><a href="/revoke">Revoke current credentials</a></td>' +
		'<td>Revoke the access token associated with the current user ' +
		'    session. After revoking credentials, if you go to the test ' +
		'    page, you should see an <code>invalid_grant</code> error.' +
		'</td></tr>' +
		'<tr><td><a href="/clear">Clear Flask session credentials</a></td>' +
		'<td>Clear the access token currently stored in the user session. ' +
		'    After clearing the token, if you <a href="/test">test the ' +
		'    API request</a> again, you should go back to the auth flow.' +
		'</td></tr></table>')




# Tienes que crear esta variable si no la tienes, en heroku no hace falta.
# Ponemos en el terminal el siguiente comando para especificar el puerto de la web.
#   $ export PORT=8080
port=os.environ["PORT"]

app.run('0.0.0.0', int(port), debug=True)


