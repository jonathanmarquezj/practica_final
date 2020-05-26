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



CLIENT_SECRETS_FILE='client_secret_heroku.json'
SCOPES=['https://www.googleapis.com/auth/calendar']

app.secret_key = '6qdL7nEDswA88vdnx-WIUdJB'

#-------------------------------------------------------------------
#     WEB
#-------------------------------------------------------------------

#INICIO
@app.route('/', methods=["GET", "POST"])
def inicio():# Miramos si existe el token, en caso contrario tendremos que crearlo
	if 'credentials' not in flask.session:
		return flask.redirect('authorize')
	del flask.session['credentials']

	return flask.render_template("index.html")


#SELECCIONAR CALENDARIO
@app.route('/seleccionarCalendario', methods=["GET", "POST"])
def seleccionarCalendario():
	# Miramos si existe el token, en caso contrario tendremos que crearlo
	if 'credentials' not in flask.session:
		return flask.redirect('authorize')
	
	return flask.render_template("seleccionarCalendario.html", calendarios=listarCalendarios())

#CALENDARIO
@app.route('/calendario', methods=["GET", "POST"])
@app.route('/calendario/<mensaje>', methods=["GET", "POST"])
@app.route('/calendario/<mensaje>/<calendar_id>', methods=["GET", "POST"])
def calendario(mensaje=None, calendar_id=None):
	# Para mirar si tenemos las credenciales
	if 'credentials' not in flask.session:
		return flask.redirect('authorize')

	# Miramos si a enviado el ID del calendario por post
	if flask.request.method == "POST":
		calendar_id=flask.request.form['calendar_id']
	# En el caso de que no tengamos el ID del calendario tanto por POST como por GET, lo mandamos a que lo seleccione
	if calendar_id==None and flask.request.method != "POST":
		return flask.redirect(flask.url_for('seleccionarCalendario'))

	# Creamos el archivo "static/eventos.json" que sera donde estaran los eventos
	solicitarEventos(calendar_id)

	return flask.render_template("calendario.html", mensaje=mensaje, calendar_id=calendar_id)




# AÑADIR EVENTO EN EL CALENDARIO
@app.route('/anadirEvento/<calendar_id>', methods=["GET", "POST"])
@app.route('/anadirEvento/<mensaje>/<calendar_id>', methods=["GET", "POST"])
def anadirEvento(calendar_id, mensaje=None):
	# Miramos si existe el token, en caso contrario tendremos que crearlo
	if 'credentials' not in flask.session:
		return flask.redirect('authorize')
	# Miramos si envio el formulario para insertar los datos
	if flask.request.method == "POST":
		calendar_id=flask.request.form['calendar_id']
		titulo=flask.request.form['titulo']
		fechaInicio=flask.request.form['fechaInicio']
		horaInicio=flask.request.form['horaInicio']
		fechaFin=flask.request.form['fechaFin']
		horaFin=flask.request.form['horaFin']

		# Comprobamos la fecha
		if fechaInicio.replace('-','') > fechaFin.replace('-',''):
			# Si pone mal la fecha le ponemos un mensaje
			return flask.redirect(flask.url_for('anadirEvento', mensaje='Lo sentimos pero no se pudo insertar el evento. La fecha inicio no pueder ser mayor a la fecha fin', calendar_id=calendar_id))
		else:
			# Si todo es correcto metemos el evento y lo mandamos al calendario
			anadirEvento(titulo, fechaInicio, horaInicio, fechaFin, horaFin, calendar_id)
			# Le pedimos al calendario los eventos de nuevo 
			solicitarEventos(calendar_id)
			return flask.redirect(flask.url_for('calendario', mensaje='Evento insertado', calendar_id=calendar_id))

	else:
		return flask.render_template("anadirEvento.html", mensaje=mensaje, calendar_id=calendar_id)


# MODIFICAR EVENTO EN EL CALENDARIO
@app.route('/modificarEvento/<id_evento>/<calendar_id>', methods=["GET", "POST"])
@app.route('/modificarEvento/<id_evento>/<calendar_id>/<mensaje>', methods=["GET", "POST"])
def modificarEvento(id_evento, calendar_id, mensaje=None):
	# Miramos si existe el token, en caso contrario tendremos que crearlo
	if 'credentials' not in flask.session:
		return flask.redirect('authorize')
	# Miramos si envio el formulario para insertar los datos
	if flask.request.method == "POST":
		id_evento=flask.request.form['id_evento']
		titulo=flask.request.form['titulo']
		fechaInicio=flask.request.form['fechaInicio']
		horaInicio=flask.request.form['horaInicio']
		fechaFin=flask.request.form['fechaFin']
		horaFin=flask.request.form['horaFin']
		calendar_id=flask.request.form['calendar_id']

		# Comprobamos la fecha
		if fechaInicio.replace('-','') > fechaFin.replace('-',''):
			# Si pone mal la fecha le ponemos un mensaje
			return flask.redirect(flask.url_for('modificarEvento', mensaje='Lo sentimos pero no se pudo insertar el evento. La fecha inicio no pueder ser mayor a la fecha fin', id_evento=id_evento, titulo=titulo, fechaInicio=fechaInicio, horaInicio=horaInicio, fechaFin=fechaFin, horaFin=horaFin, calendar_id=calendar_id))
		else:
			# Si todo es correcto metemos el evento y lo mandamos al calendario
			actualizarEvento(id_evento, titulo, fechaInicio, horaInicio, fechaFin, horaFin, calendar_id)
			# Le pedimos al calendario los eventos de nuevo
			solicitarEventos(calendar_id)
			return flask.redirect(flask.url_for('calendario', mensaje='Evento modificado', calendar_id=calendar_id))

	else:
		# Pedimos al calendario el evento con el id correspondiente y lo mostramos al usuario
		credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])
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


		return flask.render_template("modificarEvento.html", id_evento=id_evento, mensaje=mensaje, titulo=titulo, fechaInicio=fechaInicio, horaInicio=horaInicio, fechaFin=fechaFin, horaFin=horaFin, calendar_id=calendar_id)


# Elimina el evento del calendario
@app.route('/eliminarEvento/<calendar_id>/<event_id>', methods=["GET", "POST"])
def eliminarEvento(calendar_id, event_id):
	# Miramos si existe el token, en caso contrario tendremos que crearlo
	if 'credentials' not in flask.session:
		return flask.redirect('authorize')

	eliminarEvento(calendar_id, event_id)
	return flask.redirect(flask.url_for('calendario', mensaje='Evento eliminado', calendar_id=calendar_id))



# PARA LAS CREDENCIALES
@app.route('/authorize', methods=["GET", "POST"])
def authorize():
	flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)

	flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

	authorization_url, state = flow.authorization_url(access_type='offline',include_granted_scopes='true')

	flask.session['state'] = state

	return flask.redirect(authorization_url)



@app.route('/oauth2callback')
def oauth2callback():
	state = flask.session['state']

	flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
	flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

	authorization_response = flask.request.url
	flow.fetch_token(authorization_response=authorization_response)
	
	credentials = flow.credentials
	flask.session['credentials'] = credentials_to_dict(credentials)

	return flask.redirect(flask.url_for('inicio'))



# Elimina el archivo Token que es el que tiene el acceso al calendario
@app.route('/eliminarToken', methods=["GET", "POST"])
def eliminarToken():
	del flask.session['credentials']
	return flask.render_template("index.html")


#PARA PERSONALIZAR EL ERROR 404
@app.errorhandler(404)
def page_not_found(error):
    return "<h1>ERROR: 404</h1><br/>página no encontrada <br/><br/><a href='/'>Atras</a>"




#-------------------------------------------------------------------
#     FUNCIONES PYTHON
#-------------------------------------------------------------------

# Devuelve una lista de todos los calendarios que tiene el usuario
def listarCalendarios():
	credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])

	service = build("calendar", "v3", credentials=credentials)
	result = service.calendarList().list().execute()

	calendarios = {}
	for calendar_list_entry in result['items']:
		calendarios[calendar_list_entry['id']] = calendar_list_entry['summary']

	return calendarios

# Solicita al servidor todos los eventos del calendario
def solicitarEventos(calendar_id):
	credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])
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
	credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])
	service = build("calendar", "v3", credentials=credentials)
	# Insertamos el evento
	service.events().insert(calendarId=calendar_id, body=event).execute()

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
	credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])
	service = build("calendar", "v3", credentials=credentials)
	# Insertamos el evento
	service.events().update(calendarId=calendar_id, eventId=evento_id, body=event).execute()

# Elimina el evento
def eliminarEvento(calendar_id, event_id):
	credentials = google.oauth2.credentials.Credentials(**flask.session['credentials'])
	service = build("calendar", "v3", credentials=credentials)

	service.events().delete(calendarId=calendar_id, eventId=event_id).execute()


def credentials_to_dict(credentials):
	return {'token': credentials.token,
		'refresh_token': credentials.refresh_token,
		'token_uri': credentials.token_uri,
		'client_id': credentials.client_id,
		'client_secret': credentials.client_secret,
		'scopes': credentials.scopes}





# Tienes que crear esta variable si no la tienes, en heroku no hace falta.
# Ponemos en el terminal el siguiente comando para especificar el puerto de la web.
#   $ export PORT=8080
port=os.environ["PORT"]
if __name__ == '__main__':
	os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
	app.run('0.0.0.0', int(port), debug=True)


