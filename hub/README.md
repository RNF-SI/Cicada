# CICADA Hub — back d'exploration fédérée

Back **API seul**, sans interface. Il agrège l'index d'exploration de plusieurs
instances CICADA et sert la recherche transverse ainsi que la fiche publique
d'un plan, quelle que soit l'instance qui l'héberge.

Il accompagne l'issue **#636**.

```
   ┌──────────┐  push état complet   ┌─────────┐
   │ CICADA   │ ───────────────────► │         │
   │ RNF      │ ◄─────────────────── │   HUB   │
   └──────────┘  recherche + fiche   │         │
   ┌──────────┐                      │ (API)   │
   │ CICADA   │ ───────────────────► │         │
   │ CEN      │ ◄─────────────────── │         │
   └──────────┘                      └─────────┘
```

## Pourquoi un projet séparé

À terme l'index de recherche ne vit plus dans CICADA : chaque instance produit
ses documents et les dépose ici, et c'est ici que la recherche s'exécute. Un
projet distinct évite d'entretenir un moteur de recherche dans un logiciel qui
ne s'en sert plus, et permet au hub d'évoluer (volume, moteur) sans toucher aux
instances.

Il vit pour l'instant dans le dépôt CICADA, le temps que le contrat d'échange se
stabilise : un seul commit fait évoluer les deux côtés. Il sera extrait dans son
propre dépôt une fois le format figé.

## Ce que le hub connaît — et ce qu'il ne connaît pas

Il **ne connaît pas** les modèles métier de CICADA. Ni `PlanGestion`, ni `Enjeu`,
ni `Operation`. Il ne stocke que deux choses :

| Table | Contenu |
|---|---|
| `ccd_search.t_plan_indexe` | une ligne par plan publié : son bandeau, ses facettes, et sa **fiche rendue** en JSONB |
| `ccd_search.t_recherche_contenu` | une ligne par objet explorable (enjeu, pression, action…), rattachée à son plan |

La fiche est un **instantané publié**, pas un modèle répliqué. Les sérialiseurs
de fiche de CICADA produisent déjà un arbre JSON autonome : l'instance l'envoie
tel quel, le hub le range et le ressert. C'est ce qui permet de servir la fiche
complète d'un plan distant sans recopier ici la moitié d'`apps.plans`.

Contrepartie assumée : la fiche vieillit jusqu'à la publication suivante.

Il connaît en revanche les **référentiels nationaux** — `ref_geo` (régions,
départements) et `ref_nomenclatures` — parce que les facettes de l'exploration
s'appuient dessus et que ces référentiels sont identiques dans toutes les
instances. Ce sont les mêmes fichiers source que CICADA, montés en lecture
seule (cf. `docker-compose.hub.yml`) : les codes doivent coïncider des deux
côtés, les faire diverger casserait la résolution.

## Ce qui identifie un document

Rien n'est identifiant entre instances : `id_pg`, `id_objet`, `id_site` et
`id_organisme` sont des séquences locales. Le plan n° 42 de RNF n'a aucun
rapport avec le plan n° 42 du CEN. D'où :

- `instance_id` fait partie de toutes les clés d'unicité ;
- les zones voyagent en **codes INSEE**, re-résolus ici en identifiants locaux ;
- les sites voyagent en **codes INPN**, et sont stockés tels quels — le hub
  n'ayant aucun site à lui, il n'a rien à quoi les apparier ;
- les organismes n'ont **aucune** clé nationale tranchée : la colonne existe et
  reste vide. Recopier un identifiant local ferait matcher le mauvais organisme,
  une corruption silencieuse ; un tableau vide produit une absence visible.

## L'API

Deux familles, aux droits distincts. **Lire n'est pas écrire** : une instance
peut légitimement consulter l'exploration sans être autorisée à y publier.

### Dépôt — jeton propre à chaque instance (`X-Federation-Token`)

| Appel | Effet |
|---|---|
| `POST /api/federation/lots/` | ouvre un lot |
| `POST /api/federation/lots/{id}/plans/` | dépose une page de plans, avec leur contenu et leur fiche |
| `POST /api/federation/lots/{id}/bascule/` | publie le lot et purge les plans absents |
| `DELETE /api/federation/lots/{id}/` | abandonne le lot (ne purge rien) |

L'instance émettrice est déduite du **jeton**, jamais du corps de la requête, et
la purge est bornée à l'instance du lot. Sans ces deux bornes, un jeton valide
suffirait à purger l'index de quelqu'un d'autre.

### Lecture — jeton partagé (`X-Hub-Token`)

| Appel | Effet |
|---|---|
| `GET /api/exploration/contenus/` | recherche dans le contenu, avec compteurs d'onglets |
| `GET /api/exploration/plans/` | recherche d'un plan par nom, site ou zone |
| `GET /api/exploration/plans/{instance}:{slug}/` | fiche publiée d'un plan |
| `GET /api/geo/zones/` | arbre régions → départements, pour le filtre |

La recherche s'exécute **en un seul passage sur l'index agrégé**. C'est ce qui
rend le tri par pertinence transverse aux instances et les compteurs d'onglets
exacts — deux choses qu'une fédération qui interrogerait chaque instance puis
fusionnerait les réponses ne peut pas garantir, faute de scores comparables.

Un plan se désigne par `instance:slug` et non par son identifiant : ni l'un ni
l'autre ne sont uniques entre déploiements, et l'identifiant interne du hub
serait unique mais pas durable — un plan dépublié puis republié en obtiendrait
un nouveau.

Ces vues n'appliquent aucun périmètre utilisateur : le hub ne connaît pas les
utilisateurs. Ce qui borne l'exploration, c'est l'index lui-même et le jeton de
lecture. C'est l'instance qui relaie qui reste responsable d'authentifier son
utilisateur.

## Démarrer

```bash
docker compose -f docker-compose.hub.yml --env-file .env.hub up -d
```

L'API écoute sur http://localhost:8002. Le banc d'essai complet (deux instances
CICADA + le hub) est décrit dans [docs/MULTI_INSTANCE_LOCAL.md](../docs/MULTI_INSTANCE_LOCAL.md).

## Tests

```bash
docker compose -f docker-compose.hub.yml exec hub pytest
```
