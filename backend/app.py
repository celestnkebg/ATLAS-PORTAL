from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import bcrypt
import secrets
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATA_FILE = "data/users.json"
SYNC_FILE = "data/sync_stats.json"

# ========== FONCTIONS ==========

def load_users():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def find_user_by_email(email):
    users = load_users()
    for u in users:
        if u["email"] == email:
            return u
    return None

# ========== ROUTES ==========

@app.route("/")
def home():
    return "✅ ATLAS Portal API is running!"

@app.route("/api/test")
def test():
    return {"status": "ok", "message": "API is working"}

# ========== SYNC : ACCEPTE GET ET POST ==========
@app.route("/api/sync", methods=["GET", "POST"])
def sync_data():
    if request.method == "GET":
        return jsonify({
            "status": "ok",
            "message": "Sync endpoint is ready. Use POST to send data.",
            "last_sync": get_last_sync()
        })

    data = request.json
    if not data:
        return jsonify({"error": "Données manquantes"}), 400

    os.makedirs(os.path.dirname(SYNC_FILE), exist_ok=True)
    with open(SYNC_FILE, "w") as f:
        json.dump(data, f, indent=4)

    print(f"📥 Données reçues : {data.get('type', 'inconnu')}")
    return jsonify({"success": True, "message": "Données synchronisées"}), 200

def get_last_sync():
    if not os.path.exists(SYNC_FILE):
        return None
    with open(SYNC_FILE, "r") as f:
        data = json.load(f)
    return data.get("last_update", None)

# ========== AUTHENTIFICATION ==========

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = find_user_by_email(email)
    if not user:
        return jsonify({"success": False, "error": "Email inconnu"})

    if not bcrypt.checkpw(password.encode(), user["password"].encode()):
        return jsonify({"success": False, "error": "Mot de passe incorrect"})

    token = secrets.token_urlsafe(32)
    user["token"] = token
    user["last_login"] = datetime.now().isoformat()
    save_users(load_users())

    return jsonify({
        "success": True,
        "token": token,
        "user": {
            "email": user["email"],
            "token": user.get("token"),
            "activated": user.get("activated", False),
            "created_at": user.get("created_at")
        }
    })

@app.route("/api/activate", methods=["POST"])
def activate():
    data = request.json
    email = data.get("email")
    token_input = data.get("token")

    users = load_users()
    for u in users:
        if u["email"] == email:
            if u.get("activated", False):
                return jsonify({"success": False, "error": "Token déjà activé"})
            if u.get("token") == token_input:
                u["activated"] = True
                u["activated_at"] = datetime.now().isoformat()
                save_users(users)
                return jsonify({"success": True, "message": "Token activé avec succès"})
            else:
                return jsonify({"success": False, "error": "Token invalide"})

    return jsonify({"success": False, "error": "Utilisateur introuvable"})

@app.route("/api/user/<email>", methods=["GET"])
def get_user(email):
    user = find_user_by_email(email)
    if not user:
        return jsonify({"error": "Utilisateur introuvable"}), 404
    return jsonify({
        "email": user["email"],
        "activated": user.get("activated", False),
        "created_at": user.get("created_at"),
        "token": user.get("token")
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
