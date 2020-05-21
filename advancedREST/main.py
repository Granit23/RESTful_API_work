# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime

from flask import Flask, render_template, request, jsonify, make_response, Response
from google.auth.transport import requests
from google.cloud import datastore
import google.oauth2.id_token
import json
import constants
from json2html import *

firebase_request_adapter = requests.Request()

client = datastore.Client()

app = Flask(__name__)


@app.route('/')
def index():
    return "Please navigate to /boats to start using this API"\

@app.route('/boats', methods=['POST','GET'])
def boats_get_post():
    if request.method == 'POST':
        if request.is_json == False:
          return {"Error": 'Incorrect media type, only JSON format accepted'}, 415
        else:
          content = request.get_json()
          
          # check for validation issues
          if 'name' not in content or 'type' not in content or 'length' not in content:
            return ({"Error": "The request object is missing at least one of the required attributes"}), 400
          validation_error = content_validation(content, 'boats')
          if validation_error != False:
            return validation_error

          new_boat = datastore.entity.Entity(key=client.key(constants.boats))
          new_boat.update({"name": content["name"], "type": content["type"],
              "length": content["length"]})
          client.put(new_boat)
          new_boat = add_url(new_boat, new_boat.key.id, "boats")
          return new_boat, 201
    elif request.method == 'GET':
        query = client.query(kind=constants.boats)
        q_limit = int(request.args.get('limit', '3'))
        q_offset = int(request.args.get('offset', '0'))
        l_iterator = query.fetch(limit=q_limit, offset=q_offset)
        pages = l_iterator.pages
        results = list(next(pages))
        if l_iterator.next_page_token:
          next_offset = q_offset + q_limit
          next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
        else:
          next_url = None
        
        for e in results:
            e = add_url(e, e.key.id, "boats")     
        output = {"boats": results}

        if next_url:
          output["next"] = next_url

        return jsonify(output)
    else:
        return {"Error": 'Method not recognized'}, 405

@app.route('/boats/<id>', methods=['GET', 'DELETE', 'PATCH', 'PUT'])
def boat_get_patch_delete(id):
    if request.method == 'GET':
        # try:
          if 'application/json' in request.accept_mimetypes or 'text/html' in request.accept_mimetypes:
            print(request.accept_mimetypes)
            boat_key = client.key(constants.boats, int(id))
            boat = client.get(key=boat_key)
            if boat == None:
                return {"Error": "No boat with this boat_id exists"}, 404
            # update load list with self links
            boat = add_url(boat, id, "boats")
            if 'application/json' in request.accept_mimetypes:
              return boat
            else:
              res = make_response(json2html.convert(json=json.dumps(boat)))
              res.headers.set('Content-Type', 'text/html')
              res.status_code = 200
              return res
          else:
            return {'Error': 'Media type requested not supported. Supported mime types are: JSON, text/html'}, 406

    elif request.method == 'PATCH':
        if request.is_json == False:
          return {'Error': 'Incorrect media type, only JSON format accepted'}, 415
        else:
          content = request.get_json()
          validation_error = content_validation(content, 'boats')
          if validation_error != False:
            return validation_error
          boat_key = client.key(constants.boats, int(id))
          boat = client.get(key=boat_key)
          if boat == None:
            return {"Error": "No boat with this boat_id exists"}, 404
          for key in content:
            if key == 'name' or key == 'type' or key == 'length':
              boat[key] = content[key]
          client.put(boat)
          boat = add_url(boat, boat.key.id, "boats")
          return boat
    elif request.method == 'PUT':
      if request.is_json == False:
          return {'Error': 'Incorrect media type, only JSON format accepted'}, 415
      else:
          content = request.get_json()
          validation_error = content_validation(content, 'boats')
          if validation_error != False:
            return validation_error
          boat_key = client.key(constants.boats, int(id))
          boat = client.get(key=boat_key)
          if boat == None:
            return {"Error": "No boat with this boat_id exists"}, 404
          if 'name' not in content or 'type' not in content or 'length' not in content:
            return {"Error": 'Incorrect number of attributes [need: name, type, and length]'}, 400
          for key in content:
            if key == 'name' or key == 'type' or key == 'length':
              boat[key] = content[key]
          client.put(boat)
          boat = add_url(boat, boat.key.id, "boats")

          res = Response(status=303, mimetype='application/json')
          res.headers["Location"] = '/boats/' + str(boat.key.id)
          return res       
    elif request.method == 'DELETE':
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        if boat == None:
            return {"Error": "No boat with this boat_id exists"}, 404
        client.delete(boat_key)
        return '',204
    else:
        return "Method not recognized"

def add_url(entity, id, entity_type):
  # url = "http://127.0.0.1:8080/" + entity_type + "/" + str(id)
  url = "https://arifig-osu-hw5.ue.r.appspot.com/" + entity_type + "/" + str(id)
  entity.update({"self": url, "id": int(id)})
  return entity


# Check if the boat name already exists,
# or if the name/type are too long
def content_validation(content, entity_type):
  if entity_type == 'boats':
    if 'type' in content:
      if isinstance(content['type'], str) != True:
        return {'Error': 'Boat type must be a string'}, 400
      if len(content['type']) > 30:
        return {'Error': 'Type must be 30 characters or less'}, 400
    if 'length' in content:
      if isinstance(content['length'], int) != True:
        return {'Error': 'Boat length must be an integer'}, 400
      if content['length'] > 9999:
        return {'Error': 'Boat length must be smaller than 9999'}, 400
    if 'name' in content:
      if isinstance(content['name'], str) != True:
        return {'Error': 'Boat name must be a string'}, 400
      if len(content['name']) > 30:
        return {'Error': 'Boat name must be 30 characters or less'}, 400
      query = client.query(kind=constants.boats)
      results = list(query.fetch())
      for boat in results:
        if boat['name'] == content['name']:
          return {'Error': "A boat with that name already exists"}, 403
    return False




if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)