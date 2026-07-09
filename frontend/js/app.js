// =========================================================
// ATLAS PORTAL - FONCTIONS PARTAGÉES
// =========================================================

const API_BASE = 'https://atlas-portal-exln.onrender.com/api';

// ========== AFFICHAGE DES COINS ==========
async function updateCoins() {
    try {
        const user = JSON.parse(localStorage.getItem('atlas_user') || '{}');
        if (user.user_id) {
            const res = await fetch(`${API_BASE}/user/${user.user_id}`);
            const data = await res.json();
            if (data.coins !== undefined) {
                document.querySelectorAll('#coinDisplay, #userCoins, #statCoins').forEach(el => {
                    if (el) el.textContent = data.coins;
                });
                user.coins = data.coins;
                localStorage.setItem('atlas_user', JSON.stringify(user));
            }
        }
    } catch (e) {
        console.log('Erreur mise à jour coins:', e);
    }
}

// ========== CHARGEMENT DES STATS ==========
async function loadStats() {
    try {
        const res = await fetch(`${API_BASE}/stats`);
        const data = await res.json();
        document.querySelectorAll('#nftCount, #statNFT').forEach(el => {
            if (el) el.textContent = data.nfts || 0;
        });
        document.querySelectorAll('#memberCount, #statMembers').forEach(el => {
            if (el) el.textContent = data.members || 0;
        });
        document.querySelectorAll('#serverCount, #statServers').forEach(el => {
            if (el) el.textContent = data.servers || 0;
        });
    } catch (e) {
        console.log('Erreur stats:', e);
    }
}

// ========== VÉRIFICATION DE CONNEXION ==========
function isLoggedIn() {
    const user = localStorage.getItem('atlas_user');
    return user && JSON.parse(user).user_id;
}

function redirectIfNotLoggedIn() {
    if (!isLoggedIn() && !window.location.pathname.includes('index.html') && !window.location.pathname.includes('login.html') && !window.location.pathname.includes('activate.html')) {
        window.location.href = 'login.html';
    }
}

// ========== DÉCONNEXION ==========
function logout() {
    localStorage.removeItem('atlas_token');
    localStorage.removeItem('atlas_user');
    window.location.href = 'login.html';
}

// ========== NAVIGATION MOBILE ==========
function initMobileNav() {
    const toggle = document.getElementById('navToggle');
    const links = document.getElementById('navLinks');
    if (toggle && links) {
        toggle.addEventListener('click', () => links.classList.toggle('open'));
    }
}

// ========== INIT ==========
document.addEventListener('DOMContentLoaded', function() {
    initMobileNav();
    redirectIfNotLoggedIn();
    updateCoins();
    loadStats();

    setInterval(updateCoins, 30000);

    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
});
