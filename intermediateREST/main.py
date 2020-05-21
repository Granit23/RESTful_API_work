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

from flask import Flask, render_template, request, jsonify
from google.auth.transport import requests
from google.cloud import datastore
import google.oauth2.id_token
import json
import constants

firebase_request_adapter = requests.Request()

client = datastore.Client()

app = Flask(__name__)


@app.route('/')
def index():
    return "Please navigate to /boats or /loads to start using this API"\

@app.route('/boats', methods=['POST','GET'])
def boats_get_post():
    if request.method == 'POST':
        try:
          content = request.get_json()
          new_boat = datastore.entity.Entity(key=client.key(constants.boats))
          if "loads" in content:
            new_boat.update({"name": content["name"], "type": content["type"], "length": content["length"], "loads": content["loads"]})
          else:
            new_boat.update({"name": content["name"], "type": content["type"], "length": content["length"], "loads": []})

          
          if new_boat["loads"] != []:
            loads_list = []
            for l in new_boat["loads"]:
              load_key = client.key(constants.loads, int(l["id"]))
              load = client.get(key=load_key)
              if load == None:
                return {"Error": "At least one load with the provided load_ids does not exist"}, 404
              elif load["carrier"] != None:
                return {"Error": "At least one load with the provided load_ids already has a carrier"}, 403
              l = add_url(l, l['id'], 'loads')
              loads_list.append(l)
          
          # add the new boat so we can get an id for it
          client.put(new_boat)
          
          new_boat = add_url(new_boat, new_boat.key.id, "boats")

          # iterate back through the loads and add the boat id to the loads carrier key
          if new_boat["loads"] != []:
            for l in new_boat["loads"]:
              load_key = client.key(constants.loads, int(l["id"]))
              load = client.get(key=load_key)
              load.update({"carrier": {"id": new_boat.key.id}})
              client.put(load)
              load.update({"carrier": {"id": new_boat.key.id, "name": new_boat["name"], "self": new_boat["self"]}})
            new_boat.update({"loads": loads_list})
                    
          # new_boat = add_url(new_boat, new_boat.key.id, "boats")
          return new_boat, 201
        except:
            return ({"Error": "The request object is missing at least one of the required attributes"}), 400
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
      
        # results = list(query.fetch())
        for b in results:
          for l in b['loads']:
            l = add_url(l, l['id'], 'loads')
          b = add_url(b, b.key.id, "boats")
        
        output = {"boats": results}

        if next_url:
          output["next"] = next_url

        return json.dumps(output)
    else:
        return 'Method not recogonized'

@app.route('/boats/<id>', methods=['GET', 'DELETE', 'PATCH'])
def boat_get_patch_delete(id):
    if request.method == 'GET':
        try:
            boat_key = client.key(constants.boats, int(id))
            boat = client.get(key=boat_key)
            if boat == None:
                return {"Error": "No boat with this boat_id exists"}, 404
            
            # update load list with self links
            load_list = []
            for l in boat["loads"]:
              l = add_url(l, l["id"], "loads")
              load_list.append(l)
            
            boat.update({"loads": load_list})
            boat = add_url(boat, id, "boats")
            return boat
        except:
            return "Internal Server Error", 500
    elif request.method == 'PATCH':
        try:
            content = request.get_json()
            boat_key = client.key(constants.boats, int(id))
            boat = client.get(key=boat_key)
            if boat == None:
              return {"Error": "No boat with this boat_id exists"}, 404
            boat.update({"name": content["name"], "type": content["type"],
                "length": content["length"]})
            client.put(boat)
            boat = add_url(boat, boat.key.id, "boats")
            return boat
        except:
            return { "Error": "The request object is missing at least one of the required attributes"}, 400 
    elif request.method == 'DELETE':
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        if boat == None:
            return {"Error": "No boat with this boat_id exists"}, 404
        
        for l in boat["loads"]:
          load_key = client.key(constants.loads, int(l["id"]))
          load = client.get(key=load_key)
          load.update({"carrier": None})
          client.put(load)
        client.delete(boat_key)
        return '',204
    else:
        return "Method not recognized"

@app.route('/loads', methods=['POST','GET'])
def loads_get_post():
    if request.method == 'POST':
        try:
          # null_boat = False
          content = request.get_json()
          new_load = datastore.entity.Entity(key=client.key(constants.loads))
          # if "carrier" in content:
          #     new_load.update({"weight": content["weight"], "content": content["content"], "delivery_date": content["delivery_date"], "carrier": content["carrier"]})
          #     boat_key = client.key(constants.boats, int(content["carrier"]["id"]))
          #     boat = client.get(key=boat_key)
          #     if boat == None:
          #       return {"Error": "No boat with this boat_id exists"}, 404                  
          # else:
          #     null_boat = True
          #     new_load.update({"weight": content["weight"], "content": content["content"], "delivery_date": content["delivery_date"], "carrier": None})
          new_load.update({"weight": content["weight"], "content": content["content"], "delivery_date": content["delivery_date"], "carrier": None})
          client.put(new_load)

          # add load to boat
          # if null_boat != True:
          #   if boat["loads"] == None:
          #     loads_array = []
          #   else:
          #     loads_array = boat["loads"]
          #   loads_array.append({"id": new_load.key.id})
          #   boat.update({"loads": loads_array})
          #   client.put(boat)
          #   new_load['carrier'] = add_url(new_load['carrier'], new_load['carrier']["id"], 'boats')
          #   new_load['carrier']['name'] = boat['name']


          new_load = add_url(new_load, new_load.key.id, "loads")
          
          return new_load, 201
        except:
            return ({"Error": "The request object is missing the required number of attributes" }), 400
    elif request.method == 'GET':
        query = client.query(kind=constants.loads)
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

        # results = list(query.fetch())
        for e in results:
          if e['carrier'] != None:
            e['carrier'] = add_url(e['carrier'], e['carrier']['id'], 'boats')
          e = add_url(e, e.key.id, "loads")
        
        output = {"loads": results}
        if next_url:
          output["next"] = next_url
        return json.dumps(output)
    else:
        return 'Method not recogonized'
            
@app.route('/loads/<id>', methods=['GET', 'DELETE', 'PATCH'])
def slip_get_patch_delete(id):
    if request.method == 'GET':
        try:
            load_key = client.key(constants.loads, int(id))
            load = client.get(key=load_key)
            if load == None:
                return {"Error": "No load with this load_id exists"}, 404
            if load["carrier"] != None:
              boat_key = client.key(constants.boats, int(load["carrier"]["id"]))
              boat = client.get(key=boat_key)
              load["carrier"] = add_url(load["carrier"], boat.key.id, "boats")
              load["carrier"]["name"] = boat["name"]
            load = add_url(load, id, "loads")
            return load
        except:
            return "Internal Server Error", 500
    elif request.method == 'DELETE':
        load_key = client.key(constants.loads, int(id))
        load = client.get(key=load_key)
        if load == None:
            return {"Error": "No load with this load_id exists"}, 404
        
        if load["carrier"] != None:
          boat_key = client.key(constants.boats, int(load["carrier"]["id"]))
          boat = client.get(key=boat_key)
          for l in boat["loads"]:
            if l["id"] == load.key.id:
              boat["loads"].remove(l)
              client.put(boat)
              break      
        client.delete(load_key)
        return '',204
    else:
        return "Method not recognized"

def add_url(entity, id, entity_type):
    url = "https://arifig-osu-hw4.ue.r.appspot.com/" + entity_type + "/" + str(id)
    # url = "http://127.0.0.1:8080/" + entity_type + "/" + str(id)
    entity.update({"self": url, "id": int(id)})
    return entity

# Managing loads
@app.route('/loads/<load_id>/<boat_id>', methods=['PUT', 'DELETE'])
def load_a_boat(load_id, boat_id):
    # assign load to boat
    if request.method == 'PUT':
      load_key = client.key(constants.loads, int(load_id))
      load = client.get(key=load_key)

      boat_key = client.key(constants.boats, int(boat_id))
      boat = client.get(key=boat_key)

      if load == None or boat == None:
        return { "Error": "The specified boat and/or load don’t exist"}, 404
      elif load['carrier'] != None:
        return {"Error": "The load is already assigned to a ship"}, 403

      # add load to ship
      load["carrier"] = {"id": boat.key.id}
      client.put(load)
      
      l = {"id": load.key.id}
      boat["loads"].append(l)
      client.put(boat)
      return '', 204
    # Remove load from boat 
    elif request.method == 'DELETE':
      load_key = client.key(constants.loads, int(load_id))
      load = client.get(key=load_key)

      boat_key = client.key(constants.boats, int(boat_id))
      boat = client.get(key=boat_key)

      found = None
      if load == None or boat == None:
        return { "Error": "No load with this load_id exists or boat with this boat_id exists"}, 404
      elif load['carrier'] == None:
        return { "Error": "No boat assigned to this load"}, 404
      
      load_ids = []

      for l in boat['loads']:
        load_ids.append(str(l["id"]))
      
      if load_id not in load_ids:
        return { "Error": "load_id not found on this boat"}, 404 
         
      for l in boat["loads"]:
        if l['id'] == load.key.id:
          boat["loads"].remove(l)
          client.put(boat)
          break
      
      load.update({'carrier': None})
      client.put(load)
      return '', 204

# view all loads for a given boat
@app.route('/boats/<boat_id>/loads', methods=['GET'])
def boat_loads(boat_id):
    if request.method == 'GET':
      boat_key = client.key(constants.boats, int(boat_id))
      boat = client.get(key=boat_key)
      if boat == None:
        return { "Error": "No boat with this boat_id exists"}, 404
      for l in boat['loads']:
        l = add_url(l, l['id'], 'loads')
      return jsonify(boat['loads']), 200


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)