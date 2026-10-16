# Documentation CICADA

Site de documentation statique construit avec [MkDocs](https://www.mkdocs.org/) et le thème
[Material](https://squidfunk.github.io/mkdocs-material/), habillé aux couleurs de CICADA
(`docs/stylesheets/cicada.css`, valeurs alignées sur `frontend/src/assets/scss/_variables.scss`).

Trois ensembles, trois onglets :

| Onglet | Contenu | Source |
|--------|---------|--------|
| **Guide utilisateur** | la notice d'utilisation (contexte, rôles, puis 4 notices : utilisateur, référent de PG, administrateur d'organisme, administrateur d'instance) | reprise **à l'identique** de la notice PDF « Notice mise en page V3 » (texte, tableaux, encadrés, 64 figures) |
| **Administration technique** | installation, infrastructure, hub, releases | à reprendre depuis `docs/*.md` (squelette pour l'instant) |
| **API** | authentification, API publique des métadonnées, référence des endpoints | pages rédigées + schéma OpenAPI généré (`docs/api/openapi.json`) |

## Où est-elle servie ?

Le site est **embarqué dans l'image frontend** (`frontend/Dockerfile`, stage `docs`) et servi par
l'Apache du conteneur sous **`/aide/`**. Chaque instance CICADA l'expose donc à
`https://<instance>/aide/`, sans réglage de vhost : le `ProxyPass /` existant suffit. Le routage
Angular exclut `/aide/` (cf. `frontend/docker/apache/httpd.conf`). Le lien « Aide » de l'en-tête de
l'application y mène.

La version déployée de la documentation est toujours celle de la version déployée de l'application.

## Travailler sur la documentation

```bash
cd documentation
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/mkdocs serve          # http://127.0.0.1:8000, rechargement à chaud
.venv/bin/mkdocs build --strict # ce que fait l'image : un lien cassé fait échouer le build
```

Ou avec la stack Docker de développement : `docker compose up docs` puis http://localhost:8001.

### Ajouter une page

1. Créer le fichier Markdown dans le bon dossier (`docs/utilisateur/notice/`, `docs/referent/`,
   `docs/admin-organisme/`, `docs/admin-instance/`, `docs/administration/`, `docs/api/`).
2. L'inscrire dans `nav:` de `mkdocs.yml` (l'ordre du menu est celui du fichier).
3. Les captures vont dans `docs/assets/figures/` ; une figure s'écrit :

```markdown
<figure markdown="span">
![Texte alternatif](../assets/figures/fig12.png){ loading=lazy }
<figcaption>Figure 12 : Page Mes demandes</figcaption>
</figure>
```

Les encadrés « 💡 » de la notice sont des admonitions `!!! tip "Titre"` ; les tableaux à en-tête
vert pâle sont des tableaux Markdown ordinaires (style global).

### Mettre à jour la référence de l'API

Le schéma OpenAPI est généré depuis le code par `drf-spectacular` et **committé** dans
`docs/api/openapi.json` (le site se construit sans Django). Après tout changement d'endpoint :

```bash
scripts/export-openapi.sh
```

Sur une instance, le schéma vivant est servi à `/api/schema/` et Swagger UI à `/api/docs/`
(utilisateur authentifié).

## Figures de la notice

Les 64 figures ont été extraites du PDF à 180 dpi (`fig01.png` … `fig64.png`, numérotation de la
notice ; `fig44a.png` est la première moitié de la planche 44, `structure-plan.png` le schéma
d'arborescence du § 3.7). Pour remplacer une capture, garder le même nom de fichier.
