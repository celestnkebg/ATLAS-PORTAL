from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import bcrypt
import secrets
from datetime import datetime
from pymongo import MongoClient

app = Flask(__name__)
CORS(app, origins="*")

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["atlas_nft"]

users_col = db["users"]
servers_col = db["servers"]
tokens_col = db["tokens"]
stats_col = db["stats"]

def find_user_by_email(email):
    return users_col.find_one({"email": email})

def get_server(guild_id):
    return servers_col.find_one({"guild_id": guild_id})

def update_server(guild_id, data):
    servers_col.update_one({"guild_id": guild_id}, {"$set": data}, upsert=True)

def update_user_coins(user_id, coins):
    users_col.update_one({"user_id": user_id}, {"$set": {"coins": coins}})

@app.route("/")
def home():
    return "✅ ATLAS Portal API is running!"

@app.route("/api/test")
def test():
    return {"status": "ok", "message": "API is working"}

@app.route("/api/sync", methods=["POST"])
def sync_data():
    data = request.json
    if not data:
        return jsonify({"error": "Données manquantes"}), 400

    sync_type = data.get("type")

    if sync_type == "full_stats":
        stats_col.update_one({}, {"$set": data}, upsert=True)
        return jsonify({"success": True}), 200

    elif sync_type == "members":
        guild_id = data.get("guild_id")
        members = data.get("members")
        if guild_id and members is not None:
            update_server(guild_id, {"members": members})
        return jsonify({"success": True}), 200

    elif sync_type == "messages":
        guild_id = data.get("guild_id")
        messages = data.get("messages")
        if guild_id and messages is not None:
            server = get_server(guild_id)
            current = server.get("messages", 0) if server else 0
            update_server(guild_id, {"messages": current + messages})
        return jsonify({"success": True}), 200

    elif sync_type == "activation":
        guild_id = data.get("guild_id")
        user_id = data.get("user_id")
        token = data.get("token")
        if guild_id and user_id and token:
            update_server(guild_id, {"token": token, "activated_by": user_id})
            users_col.update_one({"user_id": user_id}, {"$set": {"token": token, "activated": True}})
        return jsonify({"success": True}), 200

    elif sync_type == "new_user":
        email = data.get("email")
        password_hash = data.get("password")
        user_id = data.get("user_id")
        if email and password_hash and user_id:
            users_col.insert_one({
                "user_id": user_id,
                "email": email,
                "password": password_hash,
                "created_at": datetime.now().isoformat(),
                "activated": False,
                "token": None,
                "servers": [],
                "coins": 0
            })
        return jsonify({"success": True}), 200

    elif sync_type == "coins":
        guild_id = data.get("guild_id")
        coins = data.get("coins")
        if guild_id and coins is not None:
            update_server(guild_id, {"coins": coins})
            server = get_server(guild_id)
            if server and server.get("user_id"):
                update_user_coins(server["user_id"], coins)
        return jsonify({"success": True}), 200

    return jsonify({"error": "Type de sync inconnu"}), 400

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = find_user_by_email(email)
    if not user:
        return jsonify({"success": False, "error": "Email inconnu"}), 404

    if not bcrypt.checkpw(password.encode(), user["password"].encode()):
        return jsonify({"success": False, "error": "Mot de passe incorrect"}), 401

    session_token = secrets.token_urlsafe(32)
    users_col.update_one({"email": email}, {"$set": {"session_token": session_token, "last_login": datetime.now().isoformat()}})

    return jsonify({
        "success": True,
        "token": session_token,
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "activated": user.get("activated", False),
            "created_at": user.get("created_at"),
            "servers": user.get("servers", []),
            "coins": user.get("coins", 0)
        }
    })

@app.route("/api/activate", methods=["POST"])
def activate():
    data = request.json
    email = data.get("email")
    token_input = data.get("token")

    user = find_user_by_email(email)
    if not user:
        return jsonify({"success": False, "error": "Utilisateur introuvable"}), 404

    if user.get("activated", False):
        return jsonify({"success": False, "error": "Token déjà activé"}), 400

    token_data = tokens_col.find_one({"code": token_input})
    if not token_data:
        return jsonify({"success": False, "error": "Token invalide"}), 400

    if token_data.get("activated", False):
        return jsonify({"success": False, "error": "Token déjà utilisé"}), 400

    tokens_col.update_one({"code": token_input}, {"$set": {"activated": True, "activated_by": user["user_id"], "activated_at": datetime.now().isoformat()}})

    guild_id = token_data.get("guild_id")
    users_col.update_one({"user_id": user["user_id"]}, {"$set": {"activated": True, "token": token_input}})

    if guild_id:
        update_server(guild_id, {"user_id": user["user_id"], "activated": True})
        users_col.update_one({"user_id": user["user_id"]}, {"$push": {"servers": guild_id}})

    return jsonify({"success": True, "message": "Token activé avec succès !"})

@app.route("/api/user/<user_id>", methods=["GET"])
def get_user(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user:
        return jsonify({"error": "Utilisateur introuvable"}), 404
    return jsonify({
        "user_id": user["user_id"],
        "email": user["email"],
        "activated": user.get("activated", False),
        "created_at": user.get("created_at"),
        "servers": user.get("servers", []),
        "coins": user.get("coins", 0)
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
