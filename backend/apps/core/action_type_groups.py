"""
Mapping des codes TYPE_ACTION vers leurs catégories (sous-sections).
Source : Codification unique Eden 62, février 2026.

Structure Excel :
  TITRE PRINCIPAL (ex: GESTION DU PATRIMOINE NATUREL)
    Sous-titre (ex: Gestion des habitats naturels)
      Code Action (ex: IP1 - Restauration d'habitats naturels)
        Code Sous-action (ex: IP1.1 - Restauration par débroussaillage)

Ce mapping associe chaque code racine à son sous-titre.
Les sous-codes héritent du groupe de leur code parent.
"""

# Code racine → sous-titre (tel qu'il apparaît dans l'Excel)
_ROOT_CODE_TO_GROUP = {
    # === GESTION DU PATRIMOINE NATUREL ===
    # Gestion des habitats naturels
    'IP1': 'Gestion des habitats naturels',
    'IP2': 'Gestion des habitats naturels',
    'IP3': 'Gestion des habitats naturels',
    'IP4': 'Gestion des habitats naturels',
    # Gestion des espèces patrimoniales
    'IP5': 'Gestion des espèces patrimoniales',
    'IP6': 'Gestion des espèces patrimoniales',
    # Gestion des espèces invasives
    'IP7': 'Gestion des espèces invasives',
    'IP8': 'Gestion des espèces invasives',
    # Pour la faune et la flore
    'IP9': 'Pour la faune et la flore',
    'IP10': 'Pour la faune et la flore',
    # Entretien des outils de gestion
    'MS1': 'Entretien des outils de gestion',
    'MS2': 'Entretien des outils de gestion',
    'MS3': 'Entretien des outils de gestion',

    # === ANALYSE ET GESTION DES RISQUES ===
    # Prévention des risques
    'MS5': 'Prévention des risques',
    'MS6': 'Prévention des risques',
    # Analyse et veille
    'EI1': 'Analyse et veille',
    # Gestion des risques
    'CI1': 'Gestion des risques',

    # === VEILLE DU TERRITOIRE ET POLICE DE L'ENVIRONNEMENT ===
    # Actions de police
    'SP1': 'Actions de police',
    'SP2': 'Actions de police',
    # Veille du territoire
    'CS1': 'Veille du territoire',

    # === CONNAISSANCE ET SUIVI ===
    # Inventaires et suivis écologiques
    'CS2': 'Inventaires et suivis écologiques',
    'CS3': 'Inventaires et suivis écologiques',
    'CS4': 'Inventaires et suivis écologiques',
    'CS5': 'Inventaires et suivis écologiques',
    'CS6': 'Inventaires et suivis écologiques',
    'CS7': 'Inventaires et suivis écologiques',
    'CS8': 'Inventaires et suivis écologiques',
    'CS9': 'Inventaires et suivis écologiques',
    'CS10': 'Inventaires et suivis écologiques',
    'CS11': 'Inventaires et suivis écologiques',
    'CS12': 'Inventaires et suivis écologiques',
    # Étude paysagère
    'EI2': 'Étude paysagère',
    'CS13': 'Étude paysagère',
    # Étude des facteurs d'influence
    'EI3': "Étude des facteurs d'influence",
    'CS14': "Étude des facteurs d'influence",
    'EI4': "Étude des facteurs d'influence",
    'CS15': "Étude des facteurs d'influence",

    # === CRÉATION ET MAINTENANCE D'INFRASTRUCTURES ===
    # Pour l'accueil du public
    'CI2': "Pour l'accueil du public",
    'CI3': "Pour l'accueil du public",
    'CI4': "Pour l'accueil du public",
    # Pour raison technique ou de sécurité
    'CI5': 'Pour raison technique ou de sécurité',
    'CI6': 'Pour raison technique ou de sécurité',
    'CI7': 'Pour raison technique ou de sécurité',
    # Ouvrages patrimoniaux
    'CI8': 'Ouvrages patrimoniaux',
    'CI9': 'Ouvrages patrimoniaux',
    'CI10': 'Ouvrages patrimoniaux',
    'CI11': 'Ouvrages patrimoniaux',

    # === GESTION DE PROJETS ET DÉMARCHES ADMINISTRATIVES ===
    # Démarches administratives
    'MS7': 'Démarches administratives',
    # Relations partenariales
    'MS8': 'Relations partenariales',
    'MS9': 'Relations partenariales',
    'MS10': 'Relations partenariales',
    'MS11': 'Relations partenariales',
    # Stratégie foncière
    'MS12': 'Stratégie foncière',
    'MS13': 'Stratégie foncière',
    'MS14': 'Stratégie foncière',
    'MS15': 'Stratégie foncière',
    # Plan de gestion
    'EI5': 'Plan de gestion',
    'EI6': 'Plan de gestion',
    # Schéma d'accueil et plan d'interprétation
    'EI7': "Schéma d'accueil et plan d'interprétation",
    'EI8': "Schéma d'accueil et plan d'interprétation",
    # Ancrage territorial
    'EI9': 'Ancrage territorial',
    'EI10': 'Ancrage territorial',
    'MS16': 'Ancrage territorial',
    # Réglementation
    'MS17': 'Réglementation',
    'MS18': 'Réglementation',
    'MS19': 'Réglementation',
    'EI11': 'Réglementation',
    # Budget
    'MS20': 'Budget',
    'MS21': 'Budget',
    # Vie de l'équipe
    'MS22': "Vie de l'équipe",
    'MS23': "Vie de l'équipe",

    # === PARTICIPATION À DES PROGRAMMES D'ÉTUDE OU DE RECHERCHE ===
    'PR1': 'Programmes scientifiques',

    # === SENSIBILISATION, INFORMATION ET FORMATION ===
    # Éducation à la nature
    'PA1': 'Éducation à la nature',
    'PA2': 'Éducation à la nature',
    # Communication
    'CC1': 'Communication',
    'CC2': 'Communication',
}


def get_action_group(cd_nomenclature: str) -> str:
    """
    Retourne le nom du groupe (sous-titre) pour un code TYPE_ACTION donné.
    Les sous-codes héritent du groupe de leur code racine.
    Ex: 'IP1.5.1' → root='IP1' → 'Gestion des habitats naturels'
    """
    if not cd_nomenclature:
        return ''
    # Extraire le code racine (avant le premier point)
    root = cd_nomenclature.split('.')[0]
    return _ROOT_CODE_TO_GROUP.get(root, '')
