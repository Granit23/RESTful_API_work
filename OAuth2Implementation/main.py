import json
import time
import uuid

from flask import *
import requests


app = Flask(__name__)



CLIENT_ID = '236374115554-d0ps1moftdsbanpott85n7s4bt71a5ga.apps.googleusercontent.com'
CLIENT_SECRET = 'p9hyUtSxqO55laQo7qCBwi9B'
SCOPE = 'profile'
# REDIRECT_URI = 'http://localhost:5000/oauth2callback'
REDIRECT_URI = 'https://arifig-osu-hw6.ue.r.appspot.com/oauth2callback'


@app.route('/')
def index():

  return render_template('welcome.html')


@app.route('/oauth')
def oauth():
  r_data = json.loads(request.args.get('data'))
  data = []
  data.append(r_data['names'][0]['givenName'])
  data.append(r_data['names'][0]['familyName'])
  state_var = str(app.secret_key)
  data.append(state_var)
  return render_template('userInfo.html', data=data)


@app.route('/oauth2callback')
def oauth2callback():
  if 'code' not in request.args:
    # end-user requests that the client access a protected resource on the server.
    app.secret_key = str(uuid.uuid4())

    # client sends the end-user’s browser to the server along with a list of permissions the client is asking for, 
    # the client ID and a random secret phrase that the client just made up. This random secret phrase is sent as the value of a parameter named state.
    # The server asks the end-user if they are OK with giving the client the things it is asking for.
    auth_uri = ('https://accounts.google.com/o/oauth2/v2/auth?response_type=code'
                '&client_id={}&redirect_uri={}&scope={}&state={}').format(CLIENT_ID, REDIRECT_URI, SCOPE, app.secret_key)
    # The end-user is redirected back to the client with an authorization code from the server and the state parameter set to the random secret phrase that the client made up moments ago.
    return redirect(auth_uri)
  else:
    # The client verifies that the value of the state parameter is the same that it sent to this end-user and gets the authorization code from the end-user
    if request.args.get('state') == app.secret_key:

      # The client sends the authorization code along with the client secret to the server.
      auth_code = request.args.get('code')
      data = {'code': auth_code,
              'client_id': CLIENT_ID,
              'client_secret': CLIENT_SECRET,
              'redirect_uri': REDIRECT_URI,
              'grant_type': 'authorization_code'}
      r = requests.post('https://oauth2.googleapis.com/token', data=data)

      # The server sends back an access token to the client. The server associates this token with the end-user and the permissions allowed for this token.
      # The client saves the access token and sends it along with all requests for the end-user's information.
      creds = json.loads(r.text)
      headers = {'Authorization': 'Bearer {}'.format(creds['access_token'])}
      req_uri = 'https://people.googleapis.com/v1/people/me?personFields=names,emailAddresses'
      r = requests.get(req_uri, headers=headers)
      return redirect(url_for('oauth', data=r.text))
    else:
      return 'Error: Secret Key'


if __name__ == '__main__':
  import uuid
  app.secret_key = str(uuid.uuid4())
  app.debug = False
  app.run()