# Politique de confidentialité CICADA

## Introduction

Cette politique de confidentialité décrit comment CICADA collecte, utilise et protège vos données personnelles conformément au Règlement Général sur la Protection des Données (RGPD).

## Responsable du traitement

**RNF (Réserves Naturelles de France)**
Contact : contact@rnf.fr

## Données collectées

### Données techniques (collectées automatiquement, sans consentement)

Les données suivantes sont collectées automatiquement pour le suivi technique des instances :

- **Token d'instance** : Identifiant unique (UUID) généré automatiquement
- **Version de l'application** : Version installée de CICADA
- **Adresse IP** : Adresse IP publique de l'instance
- **Heartbeat** : Date et heure du dernier signal de vie
- **Statut** : Indique si l'instance est active ou non

Ces données sont **anonymes** et ne permettent pas d'identifier directement une personne physique. Elles sont collectées dans le cadre de l'intérêt légitime du responsable du traitement pour :
- Assurer le suivi technique des instances
- Détecter les problèmes techniques
- Informer les utilisateurs des mises à jour disponibles

### Données nominatives (collectées uniquement avec consentement)

Les données suivantes sont collectées **uniquement si vous donnez votre consentement** lors de l'installation :

- **Nom et prénom de l'administrateur**
- **Email de contact**
- **Nom de la structure/organisme**

Ces données permettent aux mainteneurs de CICADA de :
- Contacter les administrateurs en cas de problème critique
- Informer sur les nouvelles fonctionnalités
- Améliorer le service

## Base légale du traitement

- **Données techniques** : Intérêt légitime (article 6.1.f du RGPD)
- **Données nominatives** : Consentement (article 6.1.a du RGPD)

## Durée de conservation

- **Données techniques** : Conservées tant que l'instance est active, puis supprimées après 1 an d'inactivité
- **Données nominatives** : Conservées tant que le consentement est donné, supprimées immédiatement en cas de retrait du consentement

## Vos droits

Conformément au RGPD, vous disposez des droits suivants :

### Droit d'accès (article 15)

Vous pouvez accéder à toutes les données collectées sur votre instance via l'API :

```bash
curl -H "X-Instance-Token: VOTRE_TOKEN" \
     https://tracking.cicada.reserves-naturelles.org/api/instances/me/
```

### Droit de rectification (article 16)

Vous pouvez modifier vos données nominatives en contactant les mainteneurs ou via l'interface d'administration.

### Droit à l'effacement (article 17)

Vous pouvez demander la suppression de vos données personnelles à tout moment :

1. Via l'interface d'administration Django : `/admin/system/` → "Retirer le consentement"
2. Via l'API : `DELETE /api/instances/me/`

**Note** : La suppression des données personnelles n'affecte pas les données techniques (token, version, heartbeat) qui continuent d'être collectées.

### Droit d'opposition (article 21)

Vous pouvez vous opposer au traitement de vos données nominatives en retirant votre consentement à tout moment.

### Droit à la portabilité (article 20)

Vous pouvez demander une copie de vos données dans un format structuré.

### Droit de limitation (article 18)

Vous pouvez demander la limitation du traitement de vos données.

## Exercer vos droits

Pour exercer vos droits, contactez :

- **Email** : contact@rnf.fr
- **API** : Via les endpoints décrits ci-dessus
- **Interface** : Via `/admin/system/` dans votre instance CICADA

## Sécurité des données

Les données sont stockées sur des serveurs sécurisés avec :
- Chiffrement des connexions (HTTPS)
- Authentification par token unique par instance
- Accès restreint aux données
- Sauvegardes régulières

## Transfert de données

Les données sont stockées et traitées au sein de l'Union Européenne. Aucun transfert vers des pays tiers n'est effectué.

## Cookies et traceurs

L'API de suivi n'utilise pas de cookies. L'authentification se fait via un token unique transmis dans les en-têtes HTTP.

## Modifications de la politique

Cette politique peut être modifiée. La version actuelle est toujours disponible sur :
https://github.com/RNF-SI/Cicada/blob/main/docs/PRIVACY_POLICY.md

## Contact

Pour toute question concernant cette politique de confidentialité :

**RNF (Réserves Naturelles de France)**
Email : contact@rnf.fr

## Autorité de contrôle

Vous avez le droit d'introduire une réclamation auprès de la CNIL (Commission Nationale de l'Informatique et des Libertés) :

- Site web : https://www.cnil.fr
- Adresse : 3 Place de Fontenoy - TSA 80715, 75334 PARIS CEDEX 07
