# ATLAS Portal

Portail web pour le système ATLAS NFT – Connexion, activation des tokens, et gestion des utilisateurs.

## Structure

- `backend/` : API Flask
- `frontend/` : Interface web (HTML/CSS/JS)

## Déploiement

1. Backend sur Render
2. Frontend sur Render (static site)

## Variables d'environnement

- `SECRET_KEY` : Clé secrète Flask
- `PORT` : Port du serveur

## Commandes

```bash
cd backend
pip install -r requirements.txt
python app.py
