// gather/static/js/components.js
/**
 * Système de composants léger basé sur data-attributes.
 * Pas de dépendance externe — cohérent avec un projet Django classique.
 */

// --- Dropdown (menu utilisateur, filtres) ---
document.addEventListener("click", (e) => {
  const trigger = e.target.closest("[data-dropdown-trigger]");
  document.querySelectorAll("[data-dropdown-menu].is-open").forEach((menu) => {
    if (!trigger || menu.id !== trigger.getAttribute("data-dropdown-trigger")) {
      menu.classList.remove("is-open");
      document
        .querySelector(`[data-dropdown-trigger="${menu.id}"]`)
        ?.setAttribute("aria-expanded", "false");
    }
  });
  if (trigger) {
    const menu = document.getElementById(trigger.getAttribute("data-dropdown-trigger"));
    const estOuvert = menu?.classList.toggle("is-open");
    trigger.setAttribute("aria-expanded", estOuvert ? "true" : "false");
  }
});

// Ferme le dropdown avec Échap et lui rend le focus au déclencheur
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  document.querySelectorAll("[data-dropdown-menu].is-open").forEach((menu) => {
    menu.classList.remove("is-open");
    const trigger = document.querySelector(`[data-dropdown-trigger="${menu.id}"]`);
    trigger?.setAttribute("aria-expanded", "false");
    trigger?.focus();
  });
});

// --- Modal ---
let dernierElementFocus = null;

document.addEventListener("click", (e) => {
  const openTrigger = e.target.closest("[data-modal-open]");
  if (openTrigger) {
    dernierElementFocus = openTrigger;
    const modal = document.getElementById(openTrigger.getAttribute("data-modal-open"));
    if (modal) {
      modal.classList.add("is-open");
      modal.setAttribute("role", "dialog");
      modal.setAttribute("aria-modal", "true");
      modal.querySelector("[data-modal-focus], button, a, input")?.focus();
    }
  }
  const closeTrigger = e.target.closest("[data-modal-close]");
  if (closeTrigger) {
    closeTrigger.closest("[data-modal]")?.classList.remove("is-open");
    dernierElementFocus?.focus();
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    document.querySelectorAll("[data-modal].is-open").forEach((m) => m.classList.remove("is-open"));
    dernierElementFocus?.focus();
  }
});

// --- Toast (auto-dismiss) ---
function creerToast(message, type = "info", dureeMs = 4000) {
  const conteneur = document.getElementById("toast-container");
  if (!conteneur) return;

  const couleurs = {
    success: "bg-tertiary-50 text-tertiary-600 border-tertiary-500",
    danger: "bg-danger-50 text-danger-500 border-danger-500",
    info: "bg-info-50 text-info-500 border-info-500",
  };

  const toast = document.createElement("div");
  toast.className = `toast border-l-4 ${couleurs[type] || couleurs.info} px-4 py-3 rounded-card shadow-card mb-2 transition-opacity duration-300`;
  toast.textContent = message;
  conteneur.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, dureeMs);
}
window.creerToast = creerToast;

// --- Tabs ---
document.addEventListener("click", (e) => {
  const tab = e.target.closest("[data-tab]");
  if (!tab) return;
  const groupe = tab.closest("[data-tabs]");
  groupe.querySelectorAll("[data-tab]").forEach((t) => t.classList.remove("is-active"));
  groupe.querySelectorAll("[data-tab-panel]").forEach((p) => p.classList.add("hidden"));
  tab.classList.add("is-active");
  groupe.querySelector(`[data-tab-panel="${tab.getAttribute("data-tab")}"]`)?.classList.remove("hidden");
});
// gather/static/js/components.js — ajoute à la fin
// Connexion WebSocket notifications : allume le badge doré en temps réel
if (document.getElementById("badge-notifications")) {
  const protocole = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocole}//${window.location.host}/ws/notifications/`);

  socket.onmessage = (event) => {
    document.getElementById("badge-notifications")?.classList.remove("hidden");
    const notification = JSON.parse(event.data);
    window.dispatchEvent(new CustomEvent("gather:notification", { detail: notification }));
    if (typeof creerToast === "function") {
      creerToast(notification.titre, "info");
    }
  };
}

function setBadgeNotifications(count) {
  const badge = document.getElementById("badge-notifications");
  if (!badge) return;
  const value = Number(count) || 0;
  badge.dataset.count = String(value);
  if (value <= 0) {
    badge.classList.add("hidden");
    badge.textContent = "";
    return;
  }
  badge.classList.remove("hidden");
  badge.textContent = value > 99 ? "99+" : String(value);
}

async function chargerBadgeNotifications() {
  const badge = document.getElementById("badge-notifications");
  if (!badge) return;

  try {
    const response = await fetch("/notifications/api/?non_lues=true", {
      headers: { "ngrok-skip-browser-warning": "true" },
    });
    if (!response.ok) {
      throw new Error(`Erreur ${response.status}`);
    }
    const data = await response.json();
    setBadgeNotifications(data.non_lues_count || 0);
  } catch (error) {
    console.warn("Impossible de charger le badge de notifications :", error);
  }
}

if (document.getElementById("badge-notifications")) {
  chargerBadgeNotifications();
  window.addEventListener("gather:notification", (event) => {
    const badge = document.getElementById("badge-notifications");
    if (!badge) return;
    const current = Number(badge.dataset.count || "0") || 0;
    setBadgeNotifications(current + 1);
  });
  window.addEventListener("gather:notifications-updated", (event) => {
    setBadgeNotifications(event.detail?.count ?? 0);
  });
}

// --- Paiement Mobile Money ---
async function initierPaiement(inscriptionId) {
  const form = document.getElementById(`form-paiement-${inscriptionId}`);
  if (!form) return;

  const telephone = form.querySelector("[name=telephone]").value.trim();
  if (!telephone) {
    creerToast("Veuillez entrer votre numéro de téléphone.", "danger");
    return;
  }

  const csrfToken = form.querySelector("[name=csrfmiddlewaretoken]")?.value || "";

  try {
    const response = await fetch(`/payments/${inscriptionId}/initier/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({ telephone }),
    });

    if (!response.ok) {
      const data = await response.json();
      creerToast(data.erreur || "Erreur de paiement", "danger");
      return;
    }

    creerToast("Paiement initié ! Veuillez confirmer sur votre téléphone.", "success");
    // Démarrer le polling automatique du statut après 5 secondes
    setTimeout(() => verifierPaiement(inscriptionId), 5000);
  } catch (error) {
    creerToast("Erreur de connexion", "danger");
  }
}
window.initierPaiement = initierPaiement;

function verifierPaiement(inscriptionId, tentative = 1) {
  const MAX_TENTATIVES = 12; // ~60 secondes max

  fetch(`/payments/${inscriptionId}/verifier/`, {
    method: "GET",
    headers: { "Accept": "application/json" },
  })
    .then((response) => {
      if (!response.ok) throw new Error("Statut non OK");
      return response.json();
    })
    .then((data) => {
      if (data.statut === "reussi") {
        creerToast("Paiement confirmé ! Vous êtes inscrit.", "success");
        setTimeout(() => window.location.reload(), 1500);
      } else if (data.statut === "echoue") {
        creerToast("Le paiement a échoué. Veuillez réessayer.", "danger");
      } else if (tentative < MAX_TENTATIVES) {
        // Encore en attente — réessayer dans 5 secondes
        setTimeout(() => verifierPaiement(inscriptionId, tentative + 1), 5000);
      }
    })
    .catch(() => {
      if (tentative < MAX_TENTATIVES) {
        setTimeout(() => verifierPaiement(inscriptionId, tentative + 1), 5000);
      }
    });
}
window.verifierPaiement = verifierPaiement;
