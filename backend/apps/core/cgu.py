"""
#746 — Conditions générales d'utilisation par défaut.

Chaque instance rédige les siennes dans Administration > Paramètres ; ce texte
sert de point de départ (Markdown). Le point essentiel est la section 4 : les
données des plans saisies dans l'instance peuvent être transmises à une base
de centralisation qui les expose publiquement.
"""

CGU_PAR_DEFAUT = """\
# Conditions générales d'utilisation

## 1. Objet

Les présentes conditions générales d'utilisation (CGU) encadrent l'accès à cette instance de CICADA, application de rédaction et de suivi des plans de gestion d'espaces naturels, et son utilisation. Tout utilisateur doit les accepter avant d'utiliser l'application.

## 2. Accès au service

L'accès est réservé aux personnes disposant d'un compte validé par un administrateur. Chaque utilisateur est responsable de la confidentialité de ses identifiants et de toute action réalisée avec son compte. Un accès non autorisé ou une utilisation anormale doit être signalé sans délai à l'administrateur de l'instance.

## 3. Engagements de l'utilisateur

L'utilisateur s'engage à :

- saisir des informations exactes et à jour, dans le respect des missions de sa structure ;
- ne pas porter atteinte au fonctionnement ou à la sécurité de l'application ;
- ne déposer aucun contenu illicite, ni de données personnelles au-delà de ce qui est nécessaire à la gestion des plans ;
- respecter les droits de propriété intellectuelle des documents qu'il dépose.

## 4. Centralisation et diffusion publique des données des plans de gestion

**Les données des plans de gestion saisies dans cette instance sont transmises à une base de centralisation qui les expose publiquement.** Sont concernés notamment la structure des plans (enjeux, facteurs d'influence, pressions, objectifs, indicateurs, actions et suivis) et leurs métadonnées (nom, période, sites, structures rédactrices).

En saisissant des données dans l'application, l'utilisateur reconnaît avoir connaissance de cette diffusion et s'assure que les contenus saisis peuvent être rendus publics. Les informations sensibles (localisation précise d'espèces sensibles, données nominatives…) ne doivent pas figurer dans les champs descriptifs des plans.

## 5. Données personnelles

Les données personnelles des utilisateurs (nom, prénom, adresse électronique, organisme) sont traitées par la structure qui administre l'instance, pour la seule gestion des comptes et des droits d'accès. Elles ne sont ni cédées ni diffusées publiquement. Conformément au règlement général sur la protection des données (RGPD), chaque utilisateur dispose d'un droit d'accès, de rectification et de suppression, qu'il peut exercer depuis sa page de profil ou auprès de l'administrateur de l'instance.

## 6. Responsabilité

La structure qui administre l'instance s'efforce d'assurer la disponibilité et la sécurité du service, sans garantie d'absence d'interruption. Le contenu des plans de gestion relève de la responsabilité des structures qui les rédigent.

## 7. Évolution des CGU

Les CGU peuvent être modifiées à tout moment. Toute nouvelle version doit être acceptée par l'utilisateur à sa connexion suivante pour continuer à utiliser l'application.
"""


def cgu_par_defaut():
    """Valeur par défaut du champ (callable, pour la migration)."""
    return CGU_PAR_DEFAUT
