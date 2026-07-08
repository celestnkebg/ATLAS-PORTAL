# ============================================================
# ATLAS PORTAL - BACKEND COMPLET (Flask + MongoDB)
# ============================================================

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import bcrypt
import secrets
import json
from datetime import datetime
from pymongo import MongoClient

app = Flask(__name__)
CORS(app, origins="*")

# ========== CONNEXION MONGODB ==========
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    print("❌ MONGO_URI non défini dans les variables d'environnement")
    exit(1)

client = MongoClient(MONGO_URI)
db = client["atlas_nft"]

# Collections
users_col = db["users"]
servers_col = db["servers"]
tokens_col = db["tokens"]
stats_col = db["stats"]

# Index pour éviter les doublons
users_col.create_index("email", unique=True)
users_col.create_index("user_id", unique=True)
servers_col.create_index("guild_id", unique=True)
tokens_col.create_index("code", unique=True)

print("✅ MongoDB connecté")

# ========== FONCTIONS UTILITAIRES ==========

def find_user_by_email(email):
    return users_col.find_one({"email": email})

def find_user_by_id(user_id):
    return users_col.find_one({"user_id": user_id})

def create_user(user_id, email, password_hash):
    users_col.insert_one({
        "user_id": user_id,
        "email": email,
        "password": password_hash,
        "created_at": datetime.now().isoformat(),
        "activated": False,
        "token": None,
        "servers": []
    })

def update_user(user_id, data):
    users_col.update_one({"user_id": user_id}, {"$set": data})

def get_server(guild_id):
    return servers_col.find_one({"guild_id": guild_id})

def update_server(guild_id, data):
    servers_col.update_one({"guild_id": guild_id}, {"$set": data}, upsert=True)

def get_servers():
    return list(servers_col.find({}, {"_id": 0}))

def get_stats():
    return stats_col.find_one({}, {"_id": 0})

def save_stats(data):
    stats_col.update_one({}, {"$set": data}, upsert=True)

# ========== ROUTES ==========

@app.route("/")
def home():
    return "✅ ATLAS Portal API is running!"

@app.route("/api/test")
def test():
    return {"status": "ok", "message": "API is working", "mongodb": "connected"}

# ========== SYNC (Count Bot) ==========
@app.route("/api/sync", methods=["POST"])
def sync_data():
    data = request.json
    if not data:
        return jsonify({"error": "Données manquantes"}), 400

    sync_type = data.get("type")

    if sync_type == "full_stats":
        # Mettre à jour les stats globales
        save_stats(data)
        print(f"📥 Stats reçues : {data.get('total_members', 0)} membres")
        return jsonify({"success": True}), 200

    elif sync_type == "members":
        guild_id = data.get("guild_id")
        members = data.get("members")
        if guild_id and members is not None:
            update_server(guild_id, {"members": members, "last_member_update": datetime.now().isoformat()})
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
            update_user(user_id, {"token": token, "activated": True})
            print(f"🔑 Token {token} activé pour {user_id}")
        return jsonify({"success": True}), 200

    elif sync_type == "new_user":
        email = data.get("email")
        password_hash = data.get("password")
        user_id = data.get("user_id")
        if email and password_hash and user_id:
            try:
                create_user(user_id, email, password_hash)
                print(f"👤 Nouvel utilisateur : {email}")
            except Exception as e:
                return jsonify({"error": str(e)}), 400
        return jsonify({"success": True}), 200

    return jsonify({"error": "Type de sync inconnu"}), 400

# ========== AUTHENTIFICATION ==========

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"success": False, "error": "Email et mot de passe requis"}), 400

    user = find_user_by_email(email)
    if not user:
        return jsonify({"success": False, "error": "Email inconnu"}), 404

    if not bcrypt.checkpw(password.encode(), user["password"].encode()):
        return jsonify({"success": False, "error": "Mot de passe incorrect"}), 401

    # Générer un token de session
    session_token = secrets.token_urlsafe(32)
    update_user(user["user_id"], {"session_token": session_token, "last_login": datetime.now().isoformat()})

    return jsonify({
        "success": True,
        "token": session_token,
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "activated": user.get("activated", False),
            "created_at": user.get("created_at"),
            "servers": user.get("servers", [])
        }
    })

@app.route("/api/activate", methods=["POST"])
def activate():
    data = request.json
    email = data.get("email")
    token_input = data.get("token")

    if not email or not token_input:
        return jsonify({"success": False, "error": "Email et token requis"}), 400

    user = find_user_by_email(email)
    if not user:
        return jsonify({"success": False, "error": "Utilisateur introuvable"}), 404

    if user.get("activated", False):
        return jsonify({"success": False, "error": "Token déjà activé"}), 400

    # Vérifier si le token existe dans la base des tokens
    token_data = tokens_col.find_one({"code": token_input})
    if not token_data:
        return jsonify({"success": False, "error": "Token invalide"}), 400

    if token_data.get("activated", False):
        return jsonify({"success": False, "error": "Token déjà utilisé"}), 400

    # Marquer le token comme activé
    tokens_col.update_one({"code": token_input}, {"$set": {"activated": True, "activated_by": user["user_id"], "activated_at": datetime.now().isoformat()}})

    # Activer l'utilisateur
    update_user(user["user_id"], {"activated": True, "token": token_input})

    # Lier le serveur à l'utilisateur
    guild_id = token_data.get("guild_id")
    if guild_id:
        update_server(guild_id, {"user_id": user["user_id"], "activated": True})
        # Ajouter le serveur à la liste de l'utilisateur
        users_col.update_one({"user_id": user["user_id"]}, {"$push": {"servers": guild_id}})

    return jsonify({"success": True, "message": "Token activé avec succès !"})

# ========== DONNÉES ==========

@app.route("/api/stats", methods=["GET"])
def get_stats_route():
    stats = get_stats()
    if not stats:
        return jsonify({"total_members": 0, "total_messages": 0, "servers": []})
    return jsonify(stats)

@app.route("/api/servers", methods=["GET"])
def get_servers_route():
    servers = get_servers()
    return jsonify(servers)

@app.route("/api/user/<user_id>", methods=["GET"])
def get_user_route(user_id):
    user = find_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Utilisateur introuvable"}), 404
    return jsonify({
        "user_id": user["user_id"],
        "email": user["email"],
        "activated": user.get("activated", False),
        "created_at": user.get("created_at"),
        "servers": user.get("servers", [])
    })

@app.route("/api/user/<user_id>/servers", methods=["GET"])
def get_user_servers(user_id):
    user = find_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Utilisateur introuvable"}), 404
    servers = []
    for guild_id in user.get("servers", []):
        server = get_server(guild_id)
        if server:
            servers.append(server)
    return jsonify(servers)

# ========== LANCEMENT ==========

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
