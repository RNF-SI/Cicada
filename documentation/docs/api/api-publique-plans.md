# API publique des métadonnées des plans

L'API publique expose, **sans authentification et en lecture seule**, les métadonnées des plans de gestion d'une instance. Elle est destinée à une application tierce de gestion documentaire (par exemple DOCenCEN côté CEN).

## Activation

Elle est **fermée par défaut**. Un super administrateur l'ouvre depuis les paramètres de l'instance (case « Ouvrir l'API publique des métadonnées des plans » — voir [Paramètres de l'instance](../admin-instance/parametres.md)). Tant qu'elle est fermée, les endpoints répondent `404`.

## Ce qui est exposé — et ce qui ne l'est jamais

| Exposé | Jamais exposé |
|--------|---------------|
| Nom du plan, période (années de début et de fin), rang, version, statut | Contenu du plan (enjeux, objectifs, indicateurs, actions) |
| Sites couverts (nom, type, code INPN) et organisme rédacteur principal | Budget, financements, ressources humaines |
| Rédacteurs, relecteurs, dates de validation administrative | Suivi, mesures, réalisations |
| Identifiant stable `uuid_plan` et référence `cicada:<instance>:<uuid>` | Plans en **brouillon** |

## Endpoints

| Endpoint | Rôle |
|----------|------|
| `GET /api/public/plans/` | Liste paginée des plans (hors brouillons) |
| `GET /api/public/plans/{uuid_plan}/` | Détail des métadonnées d'un plan |

## Identifier un plan de façon stable

Chaque plan porte un identifiant **`uuid_plan`**, stable dans le temps et entre instances, et une référence lisible `cicada:<instance>:<uuid>`. Ni l'identifiant numérique interne ni le *slug* ne conviennent à une application tierce : le premier est une séquence locale à l'instance, le second suit le nom du plan et change avec lui.

```bash
curl https://<instance>/api/public/plans/
```

!!! note "Servie par l'instance, pas par le hub"

    Cette API est servie par **chaque instance** et non par le hub d'exploration fédérée, qui ne stocke ni les rédacteurs ni les dates de validation.
