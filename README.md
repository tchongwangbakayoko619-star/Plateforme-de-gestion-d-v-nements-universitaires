## 🏫 Campus Event - Plateforme de Gestion d'Événements Universitaires

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Django](https://img.shields.io/badge/Django-5.0-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Table des Matières

- [À Propos](#-à-propos)
- [Fonctionnalités](#-fonctionnalités)
- [Architecture Technique](#-architecture-technique)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [Tests](#-tests)
- [Documentation](#-documentation)
- [Contribuer](#-contribuer)
- [Licence](#-licence)

---

## 🎯 À Propos

**Campus Event** est une plateforme web complète de gestion d'événements universitaires. Elle centralise l'organisation, la publication et le suivi des événements (conférences, ateliers, journées portes ouvertes, compétitions, activités associatives) au sein d'un établissement universitaire.

### 👥 Acteurs du Système

| Acteur | Rôle | Fonctionnalités Principales |
|--------|------|----------------------------|
| 🎓 **Étudiant** | Participant | S'inscrire aux événements, consulter son historique, télécharger ses certificats |
| 🏛️ **Organisateur** | Club/Association | Créer des événements, gérer les inscriptions, contrôler les présences |
| 👑 **Administrateur** | Superviseur | Gérer les utilisateurs, superviser les événements, consulter les audits |

---

## ✨ Fonctionnalités

### 🔐 Authentification & Comptes
- ✅ Inscription par email avec vérification
- ✅ Connexion locale (email + mot de passe)
- ✅ Connexion sociale (Google, GitHub)
- ✅ Réinitialisation du mot de passe
- ✅ Gestion du profil utilisateur
- ✅ Attribution des rôles (étudiant/organisateur/admin)

### 👥 Gestion des Utilisateurs
- ✅ Import CSV des utilisateurs par l'admin
- ✅ Création manuelle des comptes
- ✅ Gestion des profils étudiants (matricule, filière, niveau)
- ✅ Gestion des profils organisateurs (club, poste, mandat)

### 📅 Gestion des Événements
- ✅ Création d'événements (titre, description, date, lieu, capacité)
- ✅ Publication, modification et annulation
- ✅ Génération automatique de QR codes pour le contrôle d'accès
- ✅ Gestion des intervenants et du programme

### 📝 Inscriptions & Présences
- ✅ Inscription et désinscription aux événements
- ✅ Vérification des places disponibles
- ✅ Contrôle de présence par QR code
- ✅ Génération de certificats de participation (PDF)

### 📊 Tableaux de Bord
- ✅ Dashboard Étudiant : événements à venir, historique, certificats
- ✅ Dashboard Organisateur : événements gérés, statistiques d'inscription
- ✅ Dashboard Administrateur : vue globale, statistiques d'utilisation

### 🔒 Sécurité & Audit
- ✅ Journalisation des connexions
- ✅ Journalisation des actions sensibles
- ✅ Protection CSRF/XSS
- ✅ Rate limiting
- ✅ Permissions granulaires par rôle

---

## 🏗️ Architecture Technique

### Stack Technologique

| Composant | Technologie | Version |
|-----------|-------------|---------|
| **Langage** | Python | 3.12 |
| **Framework** | Django | 5.0 |
| **Base de données** | PostgreSQL | 15 |
| **File d'attente** | Celery + Redis | 5.3 / 7.0 |
| **Authentification** | django-allauth | 0.61 |
| **Gestion des tâches** | Celery Beat | - |
| **Tests** | pytest + factory-boy | - |
| **Conteneurisation** | Docker | - |

### Structure du Projet

```
plateforme_universitaire_de_gestion_d_evenements/
├── gather/                          # Code source principal
│   ├── apps/                        # Applications Django
│   │   ├── users/                   # Gestion des utilisateurs
│   │   ├── students/                # Profils étudiants
│   │   ├── organizers/              # Profils organisateurs
│   │   ├── events/                  # Gestion des événements
│   │   ├── registrations/           # Inscriptions et présences
│   │   ├── notifications/           # Notifications et emails
│   │   ├── dashboard/               # Tableaux de bord
│   │   ├── audit/                   # Journalisation
│   │   └── core/                    # Fonctionnalités transversales
│   ├── config/                      # Configuration Django
│   │   ├── settings/                # Fichiers de configuration
│   │   │   ├── base.py              # Configuration commune
│   │   │   ├── local.py             # Développement
│   │   │   └── production.py        # Production
│   │   ├── urls.py                  # URLs principales
│   │   └── celery.py                # Configuration Celery
│   ├── templates/                   # Templates HTML
│   ├── static/                      # Fichiers statiques
│   ├── media/                       # Fichiers média (uploads)
│   ├── locale/                      # Traductions (FR/EN)
│   ├── requirements/                # Dépendances
│   │   ├── base.txt
│   │   ├── local.txt
│   │   └── production.txt
│   └── manage.py                    # Point d'entrée Django
├── docker-compose.yml               # Configuration Docker
├── Dockerfile                       # Image Docker
├── .env                             # Variables d'environnement
├── .env.example                     # Exemple de variables
├── pyproject.toml                   # Configuration projet Python
└── README.md                        # Ce fichier
```

---

## 🚀 Installation

### Prérequis

- Python 3.12+
- PostgreSQL 15+
- Redis 7+ (pour Celery)
- Git
- Docker & Docker Compose (optionnel)

### 1. Cloner le Projet

```bash
git clone https://github.com/tchongwangbakayoko619-star/Plateforme-de-gestion-d-v-nements-universitaires.git
cd Plateforme-de-gestion-d-v-nements-universitaires
```

### 2. Créer un Environnement Virtuel

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

### 3. Installer les Dépendances

```bash
# Mettre à jour pip
pip install --upgrade pip

# Installer les dépendances de base
pip install -r gather/requirements/base.txt

# Pour le développement
pip install -r gather/requirements/local.txt
```

### 4. Configurer les Variables d'Environnement

```bash
cp .env.example .env

# Modifier .env avec tes valeurs
nano .env
```

Exemple de `.env` :

```env
# Django
DJANGO_SECRET_KEY='django-insecure-your-secret-key-here'
DJANGO_SETTINGS_MODULE=config.settings.local

# Base de données
DATABASE_URL=postgres://user:password@localhost:5432/campus_event

# Redis
REDIS_URL=redis://localhost:6379/0

# Email
EMAIL_URL=smtp://user:password@smtp.example.com:587/

# Google OAuth
GOOGLE_OAUTH2_KEY=your-google-client-id
GOOGLE_OAUTH2_SECRET=your-google-client-secret

# GitHub OAuth
GITHUB_KEY=your-github-client-id
GITHUB_SECRET=your-github-client-secret
```

### 5. Créer la Base de Données

```bash
# Créer la base PostgreSQL
sudo -u postgres psql
CREATE DATABASE campus_event;
CREATE USER campus_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE campus_event TO campus_user;
\q

# Appliquer les migrations
cd gather
python manage.py migrate
```

### 6. Créer un Superutilisateur

```bash
python manage.py createsuperuser
# Email: admin@campus-event.com
# Mot de passe: votre-mot-de-passe
```

### 7. Lancer le Serveur

```bash
python manage.py runserver
```

Rendez-vous sur [http://localhost:8000](http://localhost:8000) pour accéder à l'application.

---

## 🐳 Docker (Alternative)

### Avec Docker Compose

```bash
# Démarrer tous les services
docker-compose -f local.yml up -d

# Appliquer les migrations
docker-compose -f local.yml run --rm django python manage.py migrate

# Créer un superutilisateur
docker-compose -f local.yml run --rm django python manage.py createsuperuser

# Accéder à l'application
# http://localhost:8000
```

---

## ⚙️ Configuration

### Paramètres Principaux

| Variable | Description | Défaut |
|----------|-------------|--------|
| `DJANGO_SECRET_KEY` | Clé secrète Django | Obligatoire |
| `DATABASE_URL` | URL de la base PostgreSQL | `postgres://...` |
| `REDIS_URL` | URL de Redis | `redis://localhost:6379` |
| `DEBUG` | Mode debug | `True` en dev, `False` en prod |
| `ALLOWED_HOSTS` | Hôtes autorisés | `localhost,127.0.0.1` |

### Internationalisation

- **Langues supportées** : Français, Anglais
- **Fuseaux horaires** : Configurable par utilisateur
- **Templates traduits** : Oui

---

## 📚 Utilisation

### 🔐 Connexion

1. **Inscription** : `/accounts/signup/`
2. **Connexion** : `/accounts/login/`
3. **Connexion sociale** : Google, GitHub

### 👑 Administration

1. Accéder à `/admin/`
2. Se connecter avec un compte superutilisateur
3. Gérer les utilisateurs, événements, inscriptions

### 📅 Gestion des Événements (Organisateur)

1. Se connecter avec un compte organisateur
2. Créer un événement via le dashboard
3. Gérer les inscriptions et les présences

### 🎓 Participation (Étudiant)

1. Se connecter avec un compte étudiant
2. Parcourir les événements à venir
3. S'inscrire à un événement
4. Scanner le QR code pour valider sa présence
5. Télécharger le certificat de participation

---

## 🧪 Tests

### Exécuter les Tests

```bash
cd gather

# Tous les tests
pytest

# Tests avec couverture
pytest --cov=apps

# Tests d'un module spécifique
pytest apps/users/tests/

# Rapport de couverture HTML
pytest --cov=apps --cov-report=html
open htmlcov/index.html
```

### Types de Tests

| Type | Fichier | Description |
|------|---------|-------------|
| **Unitaires** | `test_models.py` | Tests des modèles |
| **Unitaires** | `test_services.py` | Tests des services |
| **Intégration** | `test_views.py` | Tests des vues |

---

## 📖 Documentation

### Documentation Générale

- [Cahier des charges](docs/cahier_des_charges.md)
- [Guide d'installation](docs/installation.md)
- [Guide utilisateur](docs/user_guide.md)

### Documentation Technique

- [Architecture](docs/architecture.md)
- [Base de données](docs/database.md)
- [Déploiement](docs/deployment.md)

---

## 🤝 Contribuer

### Processus de Contribution

1. **Créer une issue** pour discuter du changement
2. **Forker le projet** et créer une branche
3. **Écrire le code** avec des tests
4. **Soumettre une Pull Request**

### Standards de Code

- **Formatage** : Black
- **Linting** : Ruff / Flake8
- **Typage** : Mypy
- **Tests** : Pytest

```bash
# Vérifier le code
ruff check .
black --check .
mypy gather

# Formater le code
black .
isort .
```

---

## 📝 Commandes Utiles

### Django

```bash
# Créer une nouvelle application
python manage.py startapp nom_app

# Créer les migrations
python manage.py makemigrations

# Appliquer les migrations
python manage.py migrate

# Accéder au shell Django
python manage.py shell

# Créer un superutilisateur
python manage.py createsuperuser

# Collecter les fichiers statiques
python manage.py collectstatic
```

### Celery

```bash
# Démarrer le worker
celery -A config.celery_app worker -l info

# Démarrer le scheduler (tâches périodiques)
celery -A config.celery_app beat -l info
```

### Tests

```bash
# Lancer tous les tests
pytest

# Tests avec couverture
pytest --cov=apps

# Tests en parallèle
pytest -n auto
```

---

## 📊 Modèle de Données

### Principales Entités

```mermaid
erDiagram
    User ||--o| Student : "a un"
    User ||--o| Organizer : "a un"
    User ||--o{ Registration : "participe"
    Organizer ||--o{ Event : "organise"
    Event ||--o{ Registration : "reçoit"
    Registration ||--o| Certificate : "génère"
    Event }o--|| Category : "appartient à"
```

### Relations Clés

| Entité | Relation | Description |
|--------|----------|-------------|
| `User` | 1:1 `Student` | Profil académique |
| `User` | 1:1 `Organizer` | Profil associatif |
| `Event` | 1:N `Registration` | Inscriptions |
| `User` | N:N `Event` | Participation |
| `Organizer` | 1:N `Event` | Organisation |

---

## 🔐 Sécurité

### Mesures Implémentées

- ✅ Mots de passe hachés (Argon2)
- ✅ Protection CSRF / XSS
- ✅ Rate limiting sur les endpoints sensibles
- ✅ Authentification par JWT pour l'API
- ✅ Journalisation des accès et actions
- ✅ Permissions granulaires par rôle
- ✅ Vérification email obligatoire

### Recommandations de Sécurité

- Utiliser HTTPS en production
- Changer régulièrement les secrets
- Limiter les tentatives de connexion
- Activer la journalisation des erreurs
- Mettre à jour régulièrement les dépendances

---

## 📦 Dépendances Principales

| Dépendance | Version | Utilisation |
|------------|---------|-------------|
| Django | 5.0 | Framework web |
| django-allauth | 0.61 | Authentification sociale |
| Celery | 5.3 | Tâches asynchrones |
| PostgreSQL | 15 | Base de données |
| Redis | 7 | Cache / Queue |
| Whitenoise | 6.6 | Fichiers statiques |

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus d'informations.

---

## 🙏 Remerciements

- [Cookiecutter Django](https://github.com/cookiecutter/cookiecutter-django) - Pour la structure de base
- La communauté Django - Pour les ressources et le support
- Tous les contributeurs du projet

---

## 📞 Contact

- **Auteur** : Tchongwang Bakayoko
- **Email** : [tchongwangbakayoko619@gmail.com]
- **GitHub** : [tchongwangbakayoko619-star](https://github.com/tchongwangbakayoko619-star)

---

## 📝 Mise à Jour

**Version** : 1.0.0  
**Dernière mise à jour** : Juillet 2026  
**Statut** : En développement

---

**🏫 Campus Event - Centraliser, Organiser, Réussir !**