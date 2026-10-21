# Administration technique

Cette partie s'adresse aux personnes qui **installent, mettent à jour et exploitent** une instance CICADA : serveurs, paquet Debian, base de données, référentiels, messagerie, raccordements externes.

<div class="tiles">

<a href="installation/" class="tile--yellow">
<strong>Installation</strong>
Installation initiale d'une instance (paquet Debian, Docker, base PostgreSQL externe, serveur Apache, import des référentiels).
</a>

<a href="infrastructure/">
<strong>Infrastructure</strong>
Qui parle à qui : instance, serveur de bases, serveur de suivi (dépôt APT), hub d'exploration fédérée, registre d'images.
</a>

<a href="releases/" class="tile--salmon">
<strong>Releases et mises à jour</strong>
Procédure de publication d'une version, dépôt APT, déploiement sur serveur.
</a>

<a href="referentiels/">
<strong>Référentiels et nomenclatures</strong>
Import et mise à jour des nomenclatures, de TaxRef, HabRef, CAMPanule et du découpage administratif.
</a>

<a href="email/" class="tile--yellow">
<strong>Envoi des emails</strong>
Configuration SMTP, capture des emails en développement (Mailpit), diagnostic.
</a>

<a href="connexion-geonature/">
<strong>Connexion par GeoNature</strong>
Ouvrir la connexion aux comptes d'un GeoNature / UsersHub.
</a>

<a href="mesure-audience/" class="tile--salmon">
<strong>Mesure d'audience</strong>
Raccorder l'instance à un Matomo, sans cookie.
</a>

<a href="hub/" class="tile--green">
<strong>Hub d'exploration fédérée</strong>
Mise en production du hub, enrôlement d'une instance, publication nocturne des plans validés.
</a>

</div>

!!! note "Guides réservés au développement"

    Les guides destinés aux développeurs (tests, design system, banc multi-instances, chaîne de release) restent dans le dossier [`docs/`](https://github.com/RNF-SI/Cicada/tree/main/docs) du dépôt.
