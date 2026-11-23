# Labby — Sources de données (Phase 0)

*Exploration menée le 23 novembre 2026. Aucun code de production n'a été écrit : seuls des scripts jetables, hors du repo, ont servi à télécharger et mesurer les pages.*

## TL;DR

- **La liste des labos IC citée dans le brief n'existe plus** (`ic-services.epfl.ch/projects/appprojectslab_admlist/IC/` → 404, même sans User-Agent). Elle est remplacée par une page publique équivalente et mieux remplie : [Projects in labs – MCS/DS/SC](https://www.epfl.ch/schools/ic/education/master/computer-science/projects-lab-mcs/), qui compte **119 lignes** réparties en 3 tableaux (labos IC, labos d'autres facultés accrédités par les sections IC, centres), chacune avec acronyme, nom, encadrant·e et **URL de la page projets**. C'est notre point de départ pour `labs.yaml`.
- **Il n'existe pas de source structurée publique.** Le bloc WordPress « EPFL Student Projects » interroge `https://isa.epfl.ch/services/v1/projects/{section}`, mais cet endpoint coupe la connexion depuis l'extérieur (probablement réservé au réseau EPFL ou aux serveurs WordPress). Les pages que j'ai trouvées n'affichent plus la liste rendue par ce bloc. La plateforme SB (`sb-projects.epfl.ch`) redirige vers une page de connexion. → On reste sur l'approche **crawl + extraction par LLM**, comme prévu.
- **Formats très hétérogènes**, ce qui confirme l'intérêt du LLM. Sur 18 pages échantillonnées : ~10 listes HTML exploitables directement, 4 pages « index » dont les projets sont sur des sous-pages, 3 restreintes ou bloquées, 1 rendue en JavaScript (Notion), 2 sans liste.
- **Le coût LLM est négligeable** avec Claude Haiku 5.5 : environ **0,25 $** pour une extraction complète d'IC et environ **1 $ à 3 $** pour toute l'EPFL. Le vrai sujet est donc la **qualité**, pas le coût.

---

## 1. Environnement

| Outil | Version | Statut |
|---|---|---|
| git | 2.56 | ✅ |
| Python | 3.15 | ✅ |
| Node.js | 26.13 (LTS) | ✅ |
| uv | — | ❌ à installer avant la Phase 1 |

## 2. Règles de crawling observées

| Domaine | robots.txt |
|---|---|
| `www.epfl.ch` | 200, vide → pas de restriction |
| `ic-services.epfl.ch`, `sti.epfl.ch`, `isa.epfl.ch` | 404 → pas de restriction |
| `sb-projects.epfl.ch` | `Disallow:` vide (mais tout le site est derrière une connexion) |

- ~60 % des URL de labos sont sur `www.epfl.ch` (WordPress EPFL). Le rate limit **par domaine** est donc le vrai goulot : à 1 requête/s, crawler IC prend quelques minutes, ce qui est acceptable.
- Les autres domaines (sites de labos, GitHub Pages, Notion, idiap.ch, mpi-sp.org…) ont chacun leur propre robots.txt : le crawler devra le lire **domaine par domaine**.
- User-Agent utilisé pendant l'exploration : `LabbyBot/0.1 (unofficial EPFL student-project index; +https://github.com/Cosmoswisss/labby)`.
- `rgl.epfl.ch` répond **403** à notre User-Agent. On le marque `blocked` et on ne contourne pas.

## 3. Liste des labos (périmètre IC)

Source : [projects-lab-mcs](https://www.epfl.ch/schools/ic/education/master/computer-science/projects-lab-mcs/) (une seule page pour les 3 masters IC : informatique, data science, systèmes de communication).

| Tableau | Lignes | Contenu |
|---|---|---|
| Labs in IC | 73 | Labos IC et joints (IC/SV, IC/SB, STI/IC…), plus 7 enseignant·es « SIN-GE » sans labo |
| Labs in other schools accredited | 39 | Labos CDM, ENAC, SB, STI, SV acceptés pour les projets IC |
| IC and associate centers | 7 | Centres (SCALA, CEDE, SDSC, Imaging, CIBM…) |

- **108 URL uniques** (certaines lignes partagent la même page : LAP ×2, INDY1/2, THL2/4/5 → `theory.epfl.ch`, SDSC ×3, et la page IPG partagée par LTHC, LTHI et SMILS).
- **9 URL pointent vers `people.epfl.ch`** (page personnelle, pas de liste de projets) → `source_type: none`.
- Plusieurs URL pointent vers la page d'accueil du labo ou vers une page « contact » (LASER, PARSA, VCA, VILAB, NLP/contact, LDM/contact…) : il n'y a probablement pas de liste publique.
- Le tableau donne aussi des **domaines IC** (AIML, CV, SP…) et des **intérêts de recherche** : c'est gratuit et utile pour la page « Labos » et pour les filtres.

**Pour le reste de l'EPFL**, il n'y a pas d'équivalent central connu. Pistes pour la Phase 5 : les pages « semester projects » des sections STI citées dans le brief, et les pages de la section de physique qui listent les labos (ex. [physics-of-biological-and-complex-systems](https://www.epfl.ch/schools/sb/sph/en/master/labs/physics-of-biological-and-complex-systems-physics-projects/)). Ordre de grandeur : **~350–400 labos** pour toute l'EPFL (à confirmer en Phase 5).

## 4. Échantillon : 18 pages projets examinées

| Labo | Format | Taille (texte nettoyé) | Observations |
|---|---|---|---|
| CVLAB | **Index** WordPress → 1 sous-page par projet | 1,3 k tokens + ~0,5 k/projet | La liste ne donne que les titres : il faut suivre les liens |
| DATA | Texte libre | 0,6 k | « Pas de liste, contactez-nous » ; message daté « Fall 2025 » (périmé) |
| DCL | Texte libre | 1,2 k | Thèmes de projets master en paragraphes, sans structure |
| DLAB | **Restreint** | 0,2 k | « Accessing the list requires EPFL credentials » |
| HEXHIVE | Liste HTML | 1,4 k | Bonne structure ; lien vers les projets terminés (à ignorer) |
| IVRL | Liste HTML riche | 1 k (+) | « Spring 2027 », date de début, description longue |
| LAP | **Index** → sous-page « available projects » | 1,2 k + 1,9 k | Sous-page datée « Updated: 03-11-2026 », encadrant + e-mail |
| LARA | **GitLab EPFL** | — | Redirige vers une connexion → `restricted` |
| LCN | **Index** → sous-pages Semester / Master | 0,1 k + 8,8 k | La page racine est vide ; tout est sur les sous-pages |
| IPG (LTHC/LTHI/SMILS) | **Index partagé** → sous-pages BA / MA | 0,25 k | Labo indiqué entre parenthèses dans le titre « (SMILS) » |
| MLO | Liste HTML + **23 PDF liés** | 4,6 k | Certaines descriptions sont dans des PDF |
| RGL | — | — | **403** pour notre User-Agent → `blocked` |
| SaCS | Liste HTML | 2,5 k | « Projects available for Spring 2027 », niveau, contact |
| TML | Liste HTML courte | 0,2 k | Extraction du contenu principal à vérifier (page de 58 kB pour 0,8 k caractères extraits) |
| VITA | **Notion** (rendu JS) | 0,25 k | Le HTML ne contient que l'en-tête ; il faudrait un navigateur headless |
| BIOROB | **Base de données** maison (filtre par mot-clé) | 7 k | Plusieurs dizaines de projets, très structurés |
| LIB | Base de données maison | **20 k** | **468 projets dont l'immense majorité terminés** (depuis 2017), avec « Abstract of the student » ; seuls 5 disponibles + 2 réservés |
| LTS2 | Tableau filtrable | 1,5 k | Colonnes Titre / Description / Encadrant / **Statut (Available / Assigned / Finished)** |

Médiane : ~1,2 k tokens par page. Moyenne hors LIB : ~1,7 k tokens.

## 5. Pièges identifiés

1. **Pages index et sous-pages** (CVLAB, LCN, LAP, IPG). Le crawler doit suivre **un niveau de liens** sur le même site, filtrés par motif d'URL ou choisis par le LLM. Sans ça, on rate une grande partie des projets.
2. **Projets terminés mélangés aux disponibles** (LIB, LTS2, HEXHIVE, DCSL). Cela gaspille des tokens et pose un **risque de données personnelles** : noms et résumés d'étudiant·es sur les projets terminés. Le prompt doit ignorer explicitement les projets terminés/assignés et ne jamais extraire de noms d'étudiant·es. Un pré-filtrage serait utile quand une page structurée le permet (LIB : ne garder que les blocs « Available »/« Reserved »).
3. **Pages partagées entre plusieurs labos** (IPG, theory.epfl.ch, SDSC). L'attribution d'un projet à un labo doit venir du **contenu** (le LLM renvoie l'acronyme) et pas seulement de l'URL. La relation page ↔ labo est **plusieurs-à-plusieurs**.
4. **Informations périmées** (DATA parle encore de « Fall 2025 »). On extrait la période académique et la date « Updated » quand elles existent, pour afficher ou filtrer les projets anciens.
5. **Pages restreintes** : GitLab EPFL, listes « EPFL credentials », SB Student Projects. On les marque `restricted` et on affiche seulement le lien.
6. **Contenu rendu en JavaScript** (Notion). En V1 : `js_rendered` + lien uniquement. Un navigateur headless (Playwright) pourra s'ajouter plus tard si plusieurs labos sont concernés.
7. **PDF liés** (MLO, BNMS…). Il faut les télécharger et en extraire le texte (pdfplumber), mais seulement quand ils sont liés depuis la page projets du labo.
8. **E-mails masqués par Cloudflare** (`[email protected]`). Sans importance : on ne stocke pas d'e-mails, seulement les noms des encadrant·es.
9. **La sélection du contenu principal compte.** Les pages WordPress EPFL font 60 à 120 kB pour 1 à 8 kB de texte utile. Il faut extraire `<main>` (ou utiliser trafilatura) avant d'envoyer au LLM, sinon les menus et pieds de page font exploser les tokens et la détection de changements (des menus qui changent déclencheraient des fausses alertes).
10. **Liens morts / domaines disparus** (`lapprojects.epfl.ch` ne résout plus). Il faut gérer les erreurs DNS et HTTP proprement et les remonter dans le rapport d'exécution.

## 6. Sources structurées investiguées

| Source | Résultat |
|---|---|
| Bloc WordPress « EPFL Student Projects » | Code source ([wp-gutenberg-epfl](https://github.com/webdacjs/wp-gutenberg-epfl), dossier `frontend/epfl-student-projects`) : il appelle `isa.epfl.ch/services/v1/projects/{section}[/search?professor=…&date-active=…]`, qui renvoie du JSON avec titre, type, statut, professeur·es. **Depuis l'extérieur, le serveur ferme la connexion** (renégociation TLS puis réponse vide), aussi bien pour cette route que pour `/services/secretariats`. Non utilisable sans le réseau EPFL, ce qui est interdit par le brief. La page de documentation du bloc affiche d'ailleurs une erreur (« Please select an API source »). |
| EPFL SB Student Projects (`sb-projects.epfl.ch`) | Redirection vers `/login` → `restricted`. |
| Ancienne liste `ic-services.epfl.ch/.../appprojectslab_admlist/IC/` | 404 (encore présente dans les index des moteurs de recherche). |
| Bases de données de labos (BIOROB, LIB, LTS2) | HTML bien structuré. Des parsers dédiés seraient possibles, mais **inutiles en V1** : le LLM s'en sort et le coût est négligeable. À reconsidérer si l'évaluation montre des erreurs sur ces pages. |

**Piste hors code (pour toi)** : écrire à IC-IT ou au service IS-Academia pour demander si un accès public en lecture seule à l'endpoint `services/v1/projects` est envisageable. Ce serait la meilleure source possible (officielle et structurée), mais elle ne couvrirait que les projets saisis dans ISA.

## 7. Volume et coût estimés

**Hypothèses** : une requête d'extraction = prompt système + schéma (~1,5 k tokens) + texte de la page (~2,5 k en moyenne, sous-pages comprises) ≈ **4 k tokens en entrée**, et ~**1 k tokens en sortie** (JSON de quelques projets). Modèle : **Claude Haiku 5.5** à 0,10 $ / 0,50 $ par million de tokens (tarif vérifié au 2026-11 ; il passe à 0,50 $ / 2,50 $ au-delà de 100 k tokens de prompt, ce qui n'arrive pas ici).

| Scénario | Pages | Entrée | Sortie | Coût |
|---|---|---|---|---|
| IC, extraction complète | ~250 (108 URL + sous-pages + PDF) | 1 M | 0,25 M | **≈ 0,25 $** |
| EPFL, extraction complète | ~1 000 | 4 M | 1 M | **≈ 0,90 $** (1–3 $ avec retries et marge) |
| EPFL, mise à jour hebdomadaire (~20 % de pages modifiées) | ~200 | 0,8 M | 0,2 M | **≈ 0,20 $** |

- L'**API Batch** (−50 %) n'est pas nécessaire à ce niveau de coût.
- **Conséquence importante** : même **Claude Sonnet 5.5** (2 $ / 10 $ par million de tokens) ne coûterait qu'environ **18 $** pour toute l'EPFL et ~4 $ par semaine. Je propose de **mesurer Haiku contre Sonnet sur le jeu d'évaluation** en Phase 2 et de choisir sur la qualité. La décision te revient.

## 8. Modèle de données ajusté

Changements par rapport au brief :

```text
Lab
  id, name, acronym
  faculty                 faculté d'appartenance (IC | STI | SB | SV | ENAC | CDM | CDH | ENT)
  joint_faculties[]       ex. ["SV"] pour un labo IC/SV           ← NOUVEAU
  accredited_for[]        sections pour lesquelles le labo est listé (IN, SC, DS…)  ← NOUVEAU
  head                    professeur·e responsable (public)       ← NOUVEAU
  ic_domains[], research_interests   (depuis la page IC, gratuit)  ← NOUVEAU
  homepage_url
  projects_url            page d'entrée projets (peut être null)
  source_type             html | html_index | pdf | js_rendered | restricted | blocked | none  ← ÉTENDU
  last_checked_at, last_changed_at, last_error             ← last_error NOUVEAU

Page  (NOUVELLE entité, côté pipeline uniquement)
  url, lab_ids[]          plusieurs labos peuvent partager une page
  parent_url              si sous-page suivie depuis un index
  content_hash, fetched_at, http_status, kind (html|pdf)

Project
  id                      hash stable (lab_id + titre normalisé)
  lab_id                  déterminé par le LLM si la page est partagée
  title, summary
  description_url         sous-page du projet si elle existe, sinon la page du labo
  project_types[]         semester_bachelor | semester_master | master_thesis | other
  domains[], skills[]
  language                EN | FR | unknown
  supervisors[]           noms publics uniquement
  status                  available | reserved | unknown   (taken/finished → projet ignoré)
  academic_period         ex. "Spring 2027"
  page_updated_at         date « Updated » affichée sur la page, si présente  ← NOUVEAU
  first_seen_at, last_seen_at
  extraction_confidence
```

- `status: taken` disparaît du modèle exporté : un projet pris ou terminé est **ignoré**, comme le demande le brief, ce qui protège aussi des données d'étudiant·es.
- Les labos `restricted`, `blocked`, `js_rendered` ou `none` apparaissent quand même sur la page « Labos », avec un lien direct.

## 9. Recommandation pour la suite

1. **Phase 1** : générer `labs.yaml` à partir de la page IC projects-lab-mcs (119 lignes → ~100 labos dédupliqués), avec un `source_type` pré-rempli par heuristique (`people.epfl.ch` → `none`, `gitlab.epfl.ch` → `restricted`, `notion.site` → `js_rendered`). Tu le relis ensuite.
2. **Crawler** : extraction du contenu principal avant le hash, suivi d'**un niveau** de liens internes (motifs `project`, `semester`, `master`, `thesis`, PDF) avec une limite par labo, robots.txt par domaine, 1 requête/s par domaine, cache disque.
3. **Extraction** : Haiku 5.5 avec sortie structurée. Le prompt demande explicitement d'ignorer les projets terminés/assignés et les noms d'étudiant·es, et de renvoyer l'acronyme du labo pour les pages partagées.
4. **Évaluation** : constituer le jeu annoté en reprenant les cas difficiles vus ici (LIB, LCN, IPG partagé, CVLAB index, LTS2 statuts, DCL texte libre), puis comparer Haiku et Sonnet.
5. **Hors V1** : headless pour Notion, parsers dédiés, demande d'accès à l'API ISA.

---

## 10. Extension à toute l'EPFL (exploration du 23 novembre 2026)

### Source principale : la liste officielle des labos

[www.epfl.ch/labs/](https://www.epfl.ch/labs/) liste **428 laboratoires** (HTML rendu côté
serveur, une ligne `.site-row` par labo) avec, pour chacun : acronyme, nom, lien vers le site
du labo, faculté(s) et institut(s) (`data-tags="STI;IEM"`).

| Faculté (principale) | Labos | Déjà dans `labs.yaml` (IC) | Nouveaux |
|---|---|---|---|
| SB | 113 | 3 | 110 |
| STI | 105 | 18 | 87 |
| ENAC | 84 | 7 | 77 |
| SV | 60 | 5 | 55 |
| IC | 45 | 31 | 14 |
| CDM | 14 | 2 | 12 |
| CDH, AVP-CP, autre | 7 | 4 | 3 |
| **Total** | **428** | **70** | **358** |

### Difficulté : trouver la page « projets » de chaque labo

Contrairement à la page IC, la liste globale renvoie vers la **page d'accueil** du labo, pas
vers sa page de projets étudiants. Il faut donc une étape de **découverte** : chercher, sur la
page d'accueil (et son menu), un lien dont le texte ou l'URL évoque des projets étudiants
(« student projects », « semester projects », « master projects / theses », « open
positions », « join us »…), puis le faire valider par la relecture humaine de `labs.yaml`.

Sources complémentaires qui donnent directement la page projets (servent aussi à mesurer la
qualité de la découverte automatique) :

- section SMT : [lab websites with semester and master projects proposals](https://sti.epfl.ch/smt/smt-lab-websites-with-semester-and-master-projects-proposals/) (tableau, ~46 labos) ;
- liste STI par institut : [sti.epfl.ch/laboratories](https://sti.epfl.ch/laboratories/) ;
- d'autres sections publient probablement une page équivalente (SEL, SMX, SGM, SIE, SV…) : à
  rechercher section par section.

### Volume et coût

~358 labos × ~2,5 pages ≈ **900 pages**, soit environ **5 à 6 M tokens** d'extraction (mesure
réelle IC : ~6 500 tokens par page). Sur un abonnement Claude Pro, l'extraction initiale doit
être **étalée sur 1 à 2 semaines** (lots de ~100 pages, garde-fou `--max-input-tokens`) ; les
mises à jour hebdomadaires restent ensuite légères (pages modifiées seulement).

### Plan proposé

1. `pipeline labs --source epfl-all` : génère les labos manquants à partir de la liste globale
   (les 114 labos IC actuels et leurs corrections manuelles sont conservés).
2. `pipeline discover` : découverte automatique de la page projets depuis la page d'accueil
   (heuristiques + listes de sections), rapport des labos sans page trouvée.
3. Relecture de `labs.yaml` (par faculté), puis crawl.
4. Évaluation : 5 à 8 pages annotées par faculté avant l'extraction complète.
5. Extraction étalée, export, et ajout des facultés dans le site (filtre déjà prêt).
