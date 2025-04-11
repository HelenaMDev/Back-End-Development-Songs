from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# HEALTH 
######################################################################
@app.route("/health", methods=["GET"])
def health():
    return {"status": "OK"}

######################################################################
# COUNT
######################################################################
@app.route("/count")
def count():
    """return length of data"""
    count = db.songs.count_documents({})

    return {"count": count}, 200


######################################################################
# ALL SONGS
######################################################################
@app.route("/song")
def songs():
    """return all songs"""
    cursor = db.songs.find()

    return parse_json({"songs": songs}), 200


######################################################################
# GET ONE SONG 
######################################################################
@app.route("/song/<int:id>")
def get_song_by_id(id):
    """return a song"""
    song = db.songs.find_one({"id": id})

    if song:
        return parse_json(song), 200

    return {"message": f"song with id {id} not found"}, 404


######################################################################
# CREATE A SONG 
######################################################################
@app.route("/song", methods=["POST"])
def create_song():
    """create a song"""
    # Get data 
    data = request.get_json()
    if not data:
        return {"message": "Invalid JSON data"}, 400

    # Check if it already exists
    song = db.songs.find_one({"id": data["id"]})
    if song:
        return  {"Message": f"song with id {song['id']} already present"}, 302

    # Insert new song
    result = db.songs.insert_one(data)
    return jsonify({
        "inserted id": {"$oid": str(result.inserted_id)}
    }), 201


######################################################################
# UPDATE A SONG 
######################################################################
@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """update a song"""
    # Get and check data 
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return {"message": "Invalid JSON data"}, 400

    if "title" not in data or "lyrics" not in data:
        return {"message": "Missing title or lyrics in payload"}, 400

    # Check if song exists
    song = db.songs.find_one({"id": id})
    if not song:
        return  {"message": "song not found"}, 404

    # If there are changes, update the document
    if data["lyrics"] != song.get("lyrics") or data["title"] != song.get("title") :
        db.songs.update_one({"id": id}, {"$set": {"title": data["title"], "lyrics": data["lyrics"]}})

        # Get updated document
        updated_song = db.songs.find_one({"id": id})
        
        return jsonify({
            "_id": {"$oid": str(updated_song["_id"])},
            "id": id,
            "title": updated_song["title"],
            "lyrics": updated_song["lyrics"]
        }), 200

    # No changes
    return jsonify({"message": "song found, but nothing updated"}), 200


######################################################################
# DELETE A SONG 
######################################################################
@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """delete a song"""

    # Check if song exists
    song = db.songs.find_one({"id": id})
    if not song:
        return  {"message": "song not found"}, 404

    result = db.songs.delete_one({"id": id})
    if result.deleted_count == 1:
        return {}, 204

