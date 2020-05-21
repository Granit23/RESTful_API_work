from google.cloud import datastore
from flask import *
from requests_oauthlib import OAuth2Session
import json
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests
import constants

# This disables the requirement to use HTTPS so that you can test locally.
import os 
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
client = datastore.Client()

# These should be copied from an OAuth2 Credential section at
# https://console.cloud.google.com/apis/credentials
client_id = r'500824948697-p3df10tt2nsrq07bm7g1c5d7529p09k5.apps.googleusercontent.com'
client_secret = r'eZ5fZkK--z5Wy95JbZa3uYvm'

# This is the page that you will use to decode and collect the info from
# the Google authentication flow
# redirect_uri = 'http://127.0.0.1:8080/oauth'
redirect_uri = 'https://arifig-osu-hw7.ue.r.appspot.com/oauth'

# These let us get basic info to identify a user and not much else
# they are part of the Google People API
scope = ['https://www.googleapis.com/auth/userinfo.profile',
             'https://www.googleapis.com/auth/userinfo.email', 'openid']
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri,
                          scope=scope)

# This link will redirect users to begin the OAuth flow with Google
@app.route('/')
def index():
    authorization_url, state = oauth.authorization_url(
        'https://accounts.google.com/o/oauth2/auth',
        # access_type and prompt are Google specific extra
        # parameters.
        access_type="offline", prompt="select_account")
    # return 'Please go <a href=%s>here</a> and authorize access.' % authorization_url
    return render_template('welcome.html', auth_url=authorization_url)

# This is where users will be redirected back to and where you can collect
# the JWT for use in future requests
@app.route('/oauth')
def oauthroute():
    token = oauth.fetch_token(
        'https://accounts.google.com/o/oauth2/token',
        authorization_response=request.url,
        client_secret=client_secret)
    req = requests.Request()

    id_info = id_token.verify_oauth2_token( 
    token['id_token'], req, client_id)

    return "Your JWT is: %s" % token['id_token']

# This page demonstrates verifying a JWT. id_info['email'] contains
# the user's email address and can be used to identify them
# this is the code that could prefix any API call that needs to be
# tied to a specific user by checking that the email in the verified
# JWT matches the email associated to the resource being accessed.
def verify_jwt(jwt, client_id):
    req = requests.Request()
    try:
        id_info = id_token.verify_oauth2_token(jwt, req, client_id)
        return str(id_info['sub'])
    except:
        return None


@app.route('/boats', methods=['POST', 'GET'])
def boats_get_post():
    if request.method == 'POST':
      if request.is_json == False:
        return {"Error": 'Incorrect media type, only JSON format accepted'}, 415
      else:
        content = request.get_json()
        
        if 'name' not in content or 'type' not in content or 'length' not in content:
          return ({"Error": "The request object is missing at least one of the required attributes"}), 400

        jwt = verify_jwt(request.headers.get('Authorization')[7:], client_id)
        if jwt == None:
          return {"Error": 'JWT failed to authenticate'}, 401
    

        new_boat = datastore.entity.Entity(key=client.key(constants.boats))
        new_boat.update({"name": content["name"], "type": content["type"],
            "length": content["length"], "owner": jwt})
        client.put(new_boat)
        return new_boat, 201
    elif request.method == 'GET':
        query = client.query(kind=constants.boats)
        results = list(query.fetch())
        for e in results:
            e.update({
              'id': e.id
            })
        return jsonify(results)
    else:
        return {"Error": 'Method not recognized'}, 405

@app.route('/owners/<owner_id>/boats', methods=['GET'])
def boats_get_owners(owner_id):
    if request.method == 'GET':

        jwt = verify_jwt(request.headers.get('Authorization')[7:], client_id)
        if jwt == None:
          return {"Error": 'JWT failed to authenticate'}, 401

        query = client.query(kind=constants.boats)
        results = list(query.fetch())
        
        owner_results = []
        for b in results:
          if b['owner'] == jwt:
            b.update({
              'id': b.id
            })
            owner_results.append(b)
        return jsonify(owner_results)
    else:
        return {"Error": 'Method not recognized'}, 405

@app.route('/boats/<id>', methods=['DELETE'])
def boat_delete(id):   
    if request.method == 'DELETE':
        jwt = verify_jwt(request.headers.get('Authorization')[7:], client_id)
        if jwt == None:
          return {"Error": 'JWT failed to authenticate'}, 401
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        
        if boat == None:
          return {"Error": "No boat with this boat_id exists"}, 403
        if boat['owner'] != jwt:
          return {"Error": "Delete failed, boat is owned by someone else"}, 403
        
        client.delete(boat_key)
        return '',204
    else:
        return "Method not recognized"


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)