# 6.7. Paramètres de l'instance et mise à jour

<p class="lead">Paramètres :</p>

La page s'ouvre depuis Administration > Paramètres, ou directement par « Paramètres » dans votre menu utilisateur (en haut à droite).


- Personnaliser l'image d'accueil de l'application et sa position (haut, centre, bas). « Rétablir l'image par défaut » (comme le retrait du logo) **supprime définitivement** l'image déposée : une confirmation est demandée ;
- Choisir la couleur du bandeau (couleurs proposées ou personnalisée, avec aperçu) et ajouter le logo de la structure, affiché en haut à gauche ;
- Choisir la couleur des exports Excel et Word (les couleurs des scores ne changent pas) ;
- Afficher le champ « ID Doc'Gestion FCEN » dans les plans (instance de la FCEN), mesure d'audience et raccordement manuel au hub ;
- **Confier l'inscription à une plateforme externe** (onglet « Fonctionnalités ») : si votre structure gère les comptes ailleurs (annuaire, portail…), indiquez son adresse. Les boutons « Créer un compte » de l'accueil et de la page de connexion l'ouvrent alors dans un nouvel onglet, et le formulaire de demande de compte de CICADA est fermé. Laisser le champ vide pour garder l'inscription dans CICADA ;
- **Rédiger les conditions générales d'utilisation** (onglet « Fonctionnalités », section « Conditions générales d'utilisation ») : des CGU par défaut sont fournies, à adapter (format Markdown : `# Titre`, `## Sous-titre`, `- liste`, `**gras**`, `[lien](https://…)`). Chaque utilisateur doit les accepter à sa connexion. **Enregistrer un texte modifié publie une nouvelle version** (confirmation demandée) : tous les utilisateurs devront l'accepter de nouveau. La page publique `/cgu` affiche la version en vigueur ;
- **Fixer la taille maximale d'un document** (onglet « Fonctionnalités », section « Documents des plans de gestion ») : de 1 à 1024 Mo, 20 Mo par défaut. Elle vaut pour les fichiers joints au plan et aux enjeux ; un fichier plus lourd est refusé ;
- **Ouvrir l'API publique des métadonnées des plans** : permet à une application tierce de gestion documentaire de lire les métadonnées des plans (jamais leur contenu, leur budget ni les brouillons) ;
- **Partager les plans avec l'exploration nationale** : voir ci-dessous.

<p class="lead">Mise à jour :</p>

Consulter la version installée et la dernière version disponible, et déclencher une mise à jour.

**Le partage avec l'exploration nationale est un engagement à l'échelle de l'instance**. Lorsque la case est cochée :

- Les plans validés de l'instance sont publiés chaque nuit vers l'exploration nationale : enjeux, facteurs, pressions, objectifs, indicateurs, actions avec leur période, suivis et protocoles ;
- **Les documents de ces plans** (documents du plan et des enjeux) deviennent consultables **sans connexion** par leur lien : l'exploration nationale n'en garde que l'adresse, le fichier reste sur votre instance. L'adresse repose sur un identifiant tiré au sort, impossible à deviner, mais quiconque la connaît peut ouvrir le document ;
- Ne sont pas partagés pour le moment : budget et financements, ressources humaines, mesures et réalisations. Si les besoins en bancarisation évoluent, les administrateurs d'instance et d'organisme seront interrogés afin d'autoriser ou non le partage d'autres données ;
- En contrepartie, les utilisateurs de l'instance explorent les plans de toutes les structures participantes.

Lorsque la case est décochée, l'exploration porte uniquement sur les plans de l'instance. Décocher la case retire immédiatement vos plans de l'exploration nationale (une confirmation est demandée) et coupe l'accès sans connexion à leurs documents : seuls les utilisateurs connectés de l'instance les ouvrent encore depuis l'exploration. Vos utilisateurs n'explorent alors plus que les plans de l'instance. Recocher republie les plans.

<figure markdown="span">
![Paramètres de l'instance](../assets/figures/fig64.webp){ loading=lazy }
<figcaption>Figure 64 : Paramètres de l'instance</figcaption>
</figure>
