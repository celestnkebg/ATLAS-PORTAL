const API_URL = 'https://atlas-portal-exln.onrender.com/api';

// Connexion
document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const message = document.getElementById('message');

    try {
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await response.json();

        if (data.success) {
            localStorage.setItem('atlas_token', data.token);
            localStorage.setItem('atlas_user', JSON.stringify(data.user));
            window.location.href = 'dashboard.html';
        } else {
            message.textContent = '❌ ' + data.error;
            message.className = 'message error';
        }
    } catch (err) {
        message.textContent = '❌ Erreur serveur. Réessaie plus tard.';
        message.className = 'message error';
    }
});

// Dashboard
if (window.location.pathname.includes('dashboard.html')) {
    const user = JSON.parse(localStorage.getItem('atlas_user') || '{}');
    if (!user.email) {
        window.location.href = 'index.html';
    }
    document.getElementById('userEmail').textContent = user.email || 'inconnu';
    document.getElementById('userToken').textContent = user.token || 'Aucun';
    document.getElementById('userStatus').textContent = user.activated ? '✅ Activé' : '⏳ En attente';
}

// Déconnexion
function logout() {
    localStorage.removeItem('atlas_token');
    localStorage.removeItem('atlas_user');
    window.location.href = 'index.html';
}

// Activation
async function activateToken() {
    const token = document.getElementById('tokenInput').value.trim();
    const message = document.getElementById('message');
    const user = JSON.parse(localStorage.getItem('atlas_user') || '{}');

    if (!token) {
        message.textContent = '❌ Entre un token.';
        message.className = 'message error';
        return;
    }

    try {
        const response = await fetch(`${API_URL}/activate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: user.email, token })
        });
        const data = await response.json();

        if (data.success) {
            message.textContent = '✅ Token activé avec succès !';
            message.className = 'message success';
            user.activated = true;
            user.token = token;
            localStorage.setItem('atlas_user', JSON.stringify(user));
            setTimeout(() => window.location.href = 'dashboard.html', 1500);
        } else {
            message.textContent = '❌ ' + data.error;
            message.className = 'message error';
        }
    } catch (err) {
        message.textContent = '❌ Erreur serveur.';
        message.className = 'message error';
    }
}
