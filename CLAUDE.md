Labby — moteur de recherche des projets étudiants dans les labos de l'EPFL — brief pour Claude Code

Ce document décrit le projet de A à Z. Lis-le en entier avant de faire quoi que ce soit. Il est enregistré à la racine du repo sous le nom CLAUDE.md : relis-le au début de chaque session.

1. Qui je suis et comment travailler avec moi
C'est mon projet et je veux comprendre ce qu'on construit, pas juste avoir du code qui marche. Donc :
Avant chaque phase, propose-moi un plan court et attends mon feu vert.
Explique brièvement tes choix techniques importants (pourquoi cette lib, cette structure, ce prompt).
Quand j'ai une action à faire (créer un compte, une clé API, installer un outil…), mets-la dans une section « 👉 À faire de ton côté », avec les étapes précises.
Fais des commits petits et fréquents avec des messages clairs (en anglais, format feat: ..., fix: ..., chore: ...).
Si une info te manque ou si un choix est ambigu, pose-moi la question plutôt que de deviner.
On communique en français. Code, noms de variables et commentaires en anglais.
2. Le projet en une phrase

Labby est un site web non officiel qui rassemble en un seul endroit tous les projets de semestre, de bachelor et de master proposés par les laboratoires de l'EPFL, avec une recherche, des filtres et (plus tard) des alertes.

Le problème
Chaque étudiant·e de Bachelor (dès BA5/BA6) et de Master doit trouver des projets dans des labos, chaque semestre.
Il n'existe aucun endroit centralisé pour toute l'EPFL. Les facultés publient seulement des listes de labos avec un lien vers chaque site (ex. IC : https://ic-services.epfl.ch/projects/appprojectslab_admlist/IC/), et chaque labo publie ses projets dans son propre format : pages HTML, tableaux, bases de données avec tags, PDF annuels, issues GitHub, pages accessibles seulement depuis le réseau EPFL, ou rien du tout.
Résultat : des heures à ouvrir des dizaines de sites, et des projets ratés (surtout interdisciplinaires) parce qu'on ne connaissait pas le labo.
Ce qui existe déjà (à connaître pour se positionner)
EPFL SB Student Projects : plateforme de la faculté SB (surtout physique) pour déposer et attribuer des projets pendant une période d'inscription. Limitée à cette faculté. → Source de données potentielle.
Bloc WordPress « EPFL Student Projects » : permet aux labos d'afficher sur leur site des projets enregistrés dans IS-Academia, filtrés par section ou par prof. Souvent la fiche renvoie juste vers le site du labo. → Il y a peut-être une source structurée derrière (à investiguer en phase 0).
make@epfl : projets proposés par des étudiant·es/associations. Hors périmètre.
Aucun agrégateur école-entière avec recherche et filtres n'a été trouvé. C'est notre valeur ajoutée.
3. Fonctionnalités cibles

L'étudiant·e peut :

chercher en texte libre (« machine learning Python ») sur tous les labos, toutes facultés ;
filtrer par : faculté / section, type de projet (semestre BA, semestre MA, projet de master, autre), domaine, compétences demandées, langue, statut (disponible / réservé / pris / inconnu), labo ;
voir une fiche propre par projet : titre, résumé, labo, encadrant·es, prérequis, type, statut, lien vers la page d'origine, date de dernière vérification ;
(V2) s'abonner à des alertes (« nouveau projet de vision par ordinateur pour BA6 ») ;
(V3) recherche sémantique / suggestions selon son profil.
4. Architecture
text
labs.yaml (liste des labos + URL de leur page projets)
      │
      ▼
[1] Crawler  ──►  cache HTML/PDF brut (disque, gitignored) + détection des changements (hash)
      │
      ▼
[2] Extraction par IA  ──►  pour chaque page nouvelle/modifiée : un LLM transforme le contenu
      │                     en liste de projets au format JSON strict (schéma pydantic)
      ▼
[3] Normalisation + validation  ──►  data/projects.json (+ data/labs.json)
      │
      ▼
[4] Site web (statique en V1)  ──►  recherche + filtres côté client
Points clés
Pourquoi un LLM : les formats sont trop hétérogènes pour écrire un parser par labo. Le LLM lit la page (texte extrait, pas le HTML brut complet) et renvoie des projets structurés. Un parser dédié reste possible pour les rares sources très structurées (ex. une base de données de labo ou une source IS-Academia).
Coût maîtrisé : on n'appelle le LLM que sur les pages qui ont changé (comparaison de hash du contenu nettoyé). Pas de clé API payante (décision du 2026-11-23) : l'extraction passe par Claude Code en mode non interactif (`claude -p --json-schema …`, modèle rapide type Haiku, outils désactivés) avec mon abonnement Claude Pro. Le quota est limité : ne jamais relancer toutes les pages sans raison, logger le nombre de tokens à chaque exécution. Garder une abstraction de « moteur » dans extract.py pour pouvoir brancher une API gratuite (ex. Gemini) si besoin.
Sorties structurées : utiliser le mode de sortie structurée / tool use de l'API avec le schéma pydantic, et rejeter/retenter les sorties invalides.
Fiabilité : constituer un jeu d'évaluation (20-30 pages annotées à la main par moi, avec ton aide) et mesurer la qualité de l'extraction (projets manqués, champs faux) avant d'élargir. C'est la partie « vraie IA » du projet.
5. Modèle de données (proposition — à ajuster après la phase 0)
text
Lab
  id                ex. "ic-dlab"
  name, acronym
  faculty           IC | STI | SB | SV | ENAC | CDM | CDH
  sections[]        sections concernées si connues
  projects_url      page "projets étudiants" du labo
  source_type       html | pdf | github | structured | none | restricted
  last_checked_at, last_changed_at

Project
  id                hash stable (lab + titre normalisé)
  lab_id
  title
  summary           résumé court (généré ou extrait)
  description_url   lien vers la page d'origine (OBLIGATOIRE)
  project_types[]   semester_bachelor | semester_master | master_thesis | other
  domains[]         ex. machine learning, robotics, security…
  skills[]          ex. Python, C++, PyTorch…
  language          EN | FR | unknown
  supervisors[]     noms tels qu'affichés publiquement
  status            available | reserved | taken | unknown
  academic_period   ex. "Spring 2027" si indiqué
  first_seen_at, last_seen_at
  extraction_confidence   score ou flags de qualité

Données personnelles : ne jamais stocker les noms d'étudiant·es (certaines pages listent les étudiants sur des projets en cours ou terminés). Seuls les noms des encadrant·es, tels qu'affichés publiquement, sont gardés. Les projets terminés/archivés sont ignorés.

6. Sources de données (à explorer en phase 0)
Listes de labos par faculté : page IC citée plus haut (avec filtre par faculté : STI, SB, IC, ENAC, CDM, CDH, SV…), pages « semester projects » des sections STI (sti.epfl.ch/sel/semester-projects, sti.epfl.ch/smt/..., sti.epfl.ch/smx/...), etc.
Pages « student projects » des labos (le gros du travail).
Bloc « EPFL Student Projects » / IS-Academia : regarder si les pages de labos qui utilisent ce bloc chargent les données depuis un endpoint public (sans authentification). Si oui, c'est une source structurée précieuse.
EPFL SB Student Projects : vérifier ce qui est accessible publiquement.
Règles de crawling (non négociables)
Respecter robots.txt.
Rate limit : ~1 requête/seconde maximum par domaine, User-Agent explicite avec le nom du projet et un contact.
Cache disque de tout ce qui est téléchargé ; ne jamais retélécharger inutilement pendant le dev.
Uniquement le contenu public : si une page demande une connexion ou n'est accessible que depuis le réseau EPFL, on la marque restricted et on affiche seulement le lien vers le labo. Ne jamais utiliser mes identifiants EPFL.
Exécution occasionnelle (manuelle, puis hebdomadaire pendant les périodes de recherche de projets), jamais en continu.
7. Stack technique
Crawler + extraction : Python 3.11+, httpx, beautifulsoup4 / trafilatura (extraction du texte principal), pypdf ou pdfplumber pour les PDF, pydantic, Claude Code CLI (`claude -p`), pytest. Dépendances avec uv.
Site V1 : Next.js (App Router) + TypeScript + Tailwind CSS, en site statique qui importe data/projects.json au build ; recherche plein texte côté client (minisearch). Pas de backend en V1.
Hébergement : Vercel (gratuit).
Automatisation : GitHub Actions (exécution manuelle + planifiée) qui relance le pipeline et ouvre une PR si les données changent. L'authentification Claude Code (jeton d'abonnement `claude setup-token`) est stockée dans les secrets GitHub.
V2 (alertes) : Supabase (Postgres + Auth par magic link limité aux adresses @epfl.ch) + envoi d'emails (ex. Resend).

Si tu as une meilleure proposition, argumente-la et demande-moi avant de changer.

8. Structure du repo (proposition)
text
labby/
├── CLAUDE.md
├── README.md
├── pipeline/
│   ├── pyproject.toml
│   ├── labs.yaml              ← liste des labos (générée puis corrigée à la main)
│   ├── src/pipeline/
│   │   ├── crawl.py           ← fetch + cache + hash
│   │   ├── extract.py         ← nettoyage du texte + appel LLM + validation
│   │   ├── models.py          ← schémas pydantic
│   │   ├── prompts/           ← prompts d'extraction versionnés
│   │   └── export.py
│   ├── eval/                  ← pages annotées à la main + script de scoring
│   ├── tests/
│   └── cache/                 ← (gitignored)
├── data/
│   ├── labs.json
│   └── projects.json
├── web/                       ← app Next.js
└── .github/workflows/
9. Feuille de route

Chaque phase se termine par : code commité, README à jour, court récap pour moi (fait / reste / à faire de mon côté).

Phase 0 — Exploration (AUCUN code de production)
Vérifier mon environnement (git, python, node, uv).
Récupérer la liste des labos IC et en examiner un échantillon (~15 pages projets) : formats rencontrés, champs disponibles, pages vides/restreintes.
Investiguer le bloc « EPFL Student Projects » (source IS-Academia publique ?) et la plateforme SB.
Estimer le volume (nombre de labos et de pages pour IC, puis pour toute l'EPFL) et le coût LLM d'une extraction complète puis d'une mise à jour hebdomadaire.
Livrable : docs/data-sources.md (formats, pièges, sources structurées trouvées, estimation de coût, modèle de données ajusté, recommandation).
Stop : attendre ma validation.
Phase 1 — Crawler (périmètre : faculté IC)
labs.yaml pour IC (généré automatiquement, puis je le relis).
Crawler avec cache, rate limit, retry, détection de changements, gestion HTML + PDF, marquage restricted / none.
Commande documentée : uv run pipeline crawl.
Phase 2 — Extraction par IA + évaluation
Prompt d'extraction + schéma pydantic + sortie structurée + validation/retry.
Jeu d'évaluation : on annote ensemble 20-30 pages ; script qui calcule précision/rappel des projets et exactitude des champs principaux.
Itérer sur le prompt jusqu'à une qualité jugée suffisante ensemble.
Export data/projects.json + rapport d'exécution (nb de labos, de projets, pages en erreur, tokens, coût).
Phase 3 — Site V1
Page principale : recherche + filtres combinables (section 3), reflétés dans l'URL (partage de recherche).
Fiche projet avec lien vers la page d'origine et date de dernière vérification.
Page « Labos » (liste des labos couverts, avec ceux sans liste publique → lien direct).
Responsive (mobile), mode sombre bienvenu, rapide.
Bandeau/footer : « Projet étudiant non officiel, non affilié à l'EPFL. Les informations peuvent être incomplètes ou périmées : la page du labo fait foi. » Pas de logo EPFL.
Page « À propos » : comment ça marche, comment un labo peut demander une correction ou un retrait.
Déploiement Vercel.
Phase 4 — Automatisation & qualité
GitHub Action : pipeline planifié (hebdomadaire) + manuel, PR automatique si changement, budget max de tokens par exécution.
CI : lint (ruff / eslint), tests, build.
Phase 5 — Extension & alertes
Étendre à STI, SB, SV, ENAC, CDM, CDH (en réévaluant la qualité à chaque faculté).
Alertes par email (Supabase + magic link @epfl.ch), désinscription en un clic.
Phase 6 — Bonus (idées, pas d'engagement)
Recherche sémantique (embeddings) : « un projet où je fais du ML appliqué à la santé ».
Suggestions selon les cours suivis / le profil.
Historique : quels labos proposent quel type de projets chaque semestre.
10. Hors périmètre / interdits
Pas de connexion à IS-Academia, Moodle, au réseau EPFL ou à tout service nécessitant mes identifiants.
Aucun nom d'étudiant·e stocké ; aucune donnée personnelle hors encadrant·es affiché·es publiquement.
Jamais de secrets commités : .env + .gitignore, secrets GitHub / variables Vercel.
Ne pas imiter l'identité visuelle de l'EPFL.
Toujours renvoyer vers la page d'origine : notre site est un index, pas une copie.
11. Ce que j'ai préparé de mon côté
[ ] Git, Python 3.11+, Node.js LTS, VS Code installés
[ ] Compte GitHub + repo vide créé (licence MIT) et cloné
[ ] Ce fichier enregistré comme CLAUDE.md à la racine
[x] Pas de clé API Anthropic : extraction via Claude Code et mon abonnement Pro (décision du 2026-11-23)
[ ] (Phase 3) Compte Vercel relié à GitHub
[ ] (Phase 5) Compte Supabase

Si un élément manque, dis-le-moi et guide-moi pas à pas.

12. Première tâche

Lance la Phase 0 : vérifie mon environnement, explore les sources (section 6) et rédige docs/data-sources.md. N'écris pas de code de production avant que j'aie validé ce document.