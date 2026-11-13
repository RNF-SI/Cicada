# 23. Rôles et droits

Qui peut voir, saisir, exporter ou faire avancer un plan. Toutes ces règles sont appliquées **côté serveur** ; l'écran ne fait que masquer ce qui serait refusé.

## Les rôles

| Rôle | Portée |
|------|--------|
| **Super admin** | Toute l'instance, y compris les paramètres, le RGPD et les référentiels |
| **Rédacteur principal** | Tous les plans, sites et organismes, en lecture et écriture, cycle de vie compris |
| **Admin organisme** | Son organisme : ses utilisateurs, ses sites, les plans des sites qu'il gère |
| **Utilisateur** | Les plans et sites auxquels il est rattaché |
| **Rédacteur externe** (#700) | Aucun plan par défaut ; demande l'accès en saisie à un plan, jamais les suivis |

**Référent** n'est pas un rôle mais un niveau d'accès : référent d'un plan (`PlanGestion.referents`, tenu en phase avec `CorRolePlan`, #789) ou d'un site (`CorRoleSite.referent`).

⚠️ `is_admin_organisme()` est vrai aussi pour le rédacteur principal : tester `is_redacteur_principal()` **avant** pour ne pas le borner à un organisme. Côté écran, utiliser `authService.hasGlobalAccess()`.

## Ce que chacun peut faire sur un plan

| Action | Qui | Où c'est vérifié |
|--------|-----|------------------|
| **Lire** le plan et toute son arborescence | Tout utilisateur lié au plan (membre, rattaché à un site, membre d'un organisme gestionnaire) | `apps/plans/access.py` (`plan_scope_q`, `scope_by_plan`), #610 |
| Lire un plan **validé** depuis l'exploration | Tout utilisateur connecté, sans données sensibles | `apps/plans/exploration.py`, #683 |
| **Écrire** dans le plan | Référents du plan, admin d'un organisme gestionnaire, rédacteur principal, super admin — **en brouillon seulement** | `user_can_write_plan`, `IsReferentOrReadOnly`, `CanModifyOnlyDraftPlan` (#248) |
| **Cycle de vie** (valider, archiver, nouvelle version…) | Référents du plan, admin organisme, rédacteur principal, super admin | `can_manage_plan_lifecycle()`, `IsReferent` |
| **Consulter les suivis** | Membres du plan, rattachés à un de ses sites | `suivi_scope_q(lecture=True)`, #740 |
| **Saisir les suivis** | Référents du plan ou d'un site, admin de l'organisme gestionnaire, RP, super admin | `suivi_scope_q()` |
| **Exporter** | Référents du plan et gestionnaires | `_can_export_plan()` |
| **Créer** un plan | Admin organisme et au-dessus ; un utilisateur rattaché à un site, sur ses sites | `CanCreatePlan` |

Écrire suppose un droit sur **ce** plan, vérifié pour l'objet modifié **et** pour chaque clé reçue (`id_pg`, `id_olt`, `metrique_id`…) : `apps/plans/ecriture.py`. La matrice complète est testée dans `tests/integrite/test_droits_ecriture.py`.

## Comptes

- Administrer un compte suppose un rang strictement supérieur et le même organisme (hors super admin) : `peut_administrer_compte()`, matrice `tests/integrite/test_comptes.py`.
- Le rôle ne change jamais par la fiche du compte : gestes dédiés ou demande de validation.

## Sessions

Jeton d'accès de 30 min renouvelé seul, session de 7 jours au plus, révocation à la déconnexion ou au changement de mot de passe, compte désactivé refusé dès la requête suivante. L'**impersonation** est en lecture seule, une heure au plus. Détail : section « Authentication & Permissions » du `CLAUDE.md`.

## Pages liées

[03. Validations](03-validations.md) (demandes d'accès), [05. Impersonnation](05-impersonnation.md), [08. Administration](08-administration.md).
