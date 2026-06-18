"""
Seeder pour les plans de gestion.
"""
import base64
import os
from datetime import date
from typing import Any, Dict, List

from django.conf import settings

from apps.core.models import Nomenclature
from apps.plans.models import PlanGestion, CorSitePg, CorRolePlan, CorPgFichier
from apps.users.models import Role, Site

from .base import BaseSeeder

# PNG 1×1 transparent valide (utilisé comme image de démonstration).
_DEMO_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
)


def _make_demo_pdf(title: str) -> bytes:
    """Génère un PDF minimal mais VALIDE (xref correct) affichant un titre.

    Sert de fichier de démonstration pour que le téléchargement fonctionne en
    local (#372) — les seeders ne posaient que les métadonnées, pas de binaire.
    """
    text = (title or 'Document de démonstration')[:80].replace('(', '').replace(')', '')
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        None,  # contenu (rempli ci-dessous)
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = (
        "BT /F1 16 Tf 60 770 Td (CICADA - " + text + ") Tj "
        "0 -28 Td /F1 11 Tf (Fichier de demonstration genere par le seed.) Tj ET"
    ).encode('latin-1', 'replace')
    objs[3] = b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"

    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += str(i).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    xref_pos = len(pdf)
    pdf += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n"
    for off in offsets:
        pdf += ("%010d 00000 n \n" % off).encode()
    pdf += (
        b"trailer\n<< /Size " + str(len(objs) + 1).encode()
        + b" /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode() + b"\n%%EOF"
    )
    return pdf


def _write_demo_fichier(chemin_abs: str, ext: str, title: str) -> int:
    """Écrit un fichier de démonstration sur le disque et renvoie sa taille."""
    ext = (ext or '').lower()
    if ext == 'pdf':
        content = _make_demo_pdf(title)
    elif ext in ('jpg', 'jpeg', 'png'):
        content = _DEMO_PNG
    else:
        content = (f"Document de démonstration CICADA : {title}\n").encode('utf-8')
    os.makedirs(os.path.dirname(chemin_abs), exist_ok=True)
    with open(chemin_abs, 'wb') as fh:
        fh.write(content)
    return len(content)


class PlansSeeder(BaseSeeder):
    """
    Crée les plans de gestion de test.

    Plans principaux (10) + plans historiques (6) pour chaînes de versions.

    Chaînes de versions:
    - Camargue (5 niveaux): Plan initial 2000-2010 (archive) → Eval mi-parcours 2000-2010 (archive)
      → Plan révisé 2010-2020 (archive) → Plan actuel 2020-2030 (valide) → Eval mi-parcours (draft)
    - Aiguilles Rouges (4 niveaux): Plan initial 2008-2018 (archive) → Plan 2018-2028 (valide)
      → Eval mi-parcours (draft) → Plan révisé (draft)
    - Vercors-Écrins (3 niveaux): Plan initial 2011-2021 (archive)
      → Plan actuel 2021-2031 (valide) → Eval mi-parcours (draft)
    - Vercors revision/draft (2 niveaux, #250/#278) : rang 1 2014-2024
      (valide + en_revision=True + étendu +1 an, next_rang_plan = rang 2) ↔
      rang 2 2026-2036 (draft). Démontre la cohabitation entre un plan validé
      en cours de révision et le brouillon du rang suivant.

    Panel évaluations mi-parcours (#276, 6 plans couvrant les variantes) :
    - Camargue eval 2005 : EVAL_MI_PARCOURS, archive (historique)
    - Camargue eval 2025 : EVAL_MI_PARCOURS, draft
    - Vercors-Écrins eval 2026 : EVAL_MI_PARCOURS, draft
    - Lac de Remoray eval 2022 : EVAL_MI_PARCOURS, avis_csrpn (workflow CSRPN)
    - Vercors 2014-2024 eval 2020 : EVAL_MI_PARCOURS, comite_consultatif
    - Aiguilles Rouges eval 2023 : modifie + is_mi_parcours=True + étendu +1 an
      (combinaison des 3 attributs orthogonaux)
    """

    name = 'plans'
    dependencies = ['users', 'sites']

    def _get_plans_data(self, users: List[Role], sites: List[Site]) -> List[Dict]:
        """Retourne les données des plans de gestion."""
        # Récupérer les nomenclatures
        eval_int = Nomenclature.objects.filter(mnemonique='Intermédiaire').first()
        eval_fin = Nomenclature.objects.filter(mnemonique='Finale').first()
        redac_gest = Nomenclature.objects.filter(mnemonique='OG').first()
        redac_be = Nomenclature.objects.filter(mnemonique='BE').first()

        plans = [
            # Plan Camargue + Brouage: super_admin referent, referent.camargue referent, admin.rnf et user.rnf membres.
            # Statut `valide` (avec eval 2025 en brouillon enfant) — chaîne cohérente avec
            # la règle « brouillon enfant uniquement sur parent validé » (#ND).
            # Pour les E2E qui font du CRUD sur des plans en brouillon, utiliser
            # un autre brouillon de la seed (Aiguilles Rouges révisé, Lac de Remoray
            # phase 2, Camargue+Brouage 2023-2033, etc.) via `findFirstDraft()`.
            {
                'nom': 'Plan de gestion 2020-2030 - Camargue',
                'annee_debut': 2020,
                'annee_fin': 2030,
                'rang': 3,
                'surface': 13117,
                'statut': 'valide',
                'version': '4',
                'gestion_partagee': True,
                'ct88': True,
                'risque_incendie': True,
                'id_evaluation': eval_int,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'RNF - Équipe Camargue',
                'redacteurs': 'Marie Dupont, Jean-Pierre Martin (RNF)',
                'relecteurs': 'CSRPN PACA, Commission Biodiversité RNF',
                'autres_contributeurs': 'Tour du Valat, SNPN, Amis des Marais du Vigueirat',
                'date_avis_csrpn': date(2020, 3, 15),
                'organismes_redacteurs_lookup': ['CEN'],
                'commentaire': 'Plan de gestion validé pour la période 2020-2030. '
                               '3ème plan successif, faisant suite au plan 2010-2020. '
                               'Enjeux principaux : habitats humides, flamant rose, '
                               'gestion hydraulique et activités traditionnelles.',
                'sites': [sites[0], sites[4]],  # Camargue + Marais de Brouage
                # Format: (user, is_referent)
                'membres': [
                    (users[0], True),   # super_admin - referent
                    (users[3], True),   # referent.camargue - referent
                    (users[1], False),  # admin.rnf - membre simple
                    (users[5], False),  # user.rnf - membre simple
                ]
            },
            # Plan Aiguilles Rouges: admin.rnf referent, super_admin membre
            {
                'nom': 'Plan de gestion 2018-2028 - Aiguilles Rouges',
                'annee_debut': 2018,
                'annee_fin': 2028,
                'rang': 2,
                'surface': 3279,
                'statut': 'valide',
                'version': '2',
                'gestion_partagee': False,
                'ct88': False,
                'risque_incendie': False,
                'id_evaluation': eval_fin,
                'id_redacteur_type': redac_be,
                'redacteur_nom': 'Cabinet Natura Consulting',
                'redacteurs': 'Cabinet Natura Consulting (F. Leroy, A. Bernard)',
                'relecteurs': 'CSRPN Auvergne-Rhône-Alpes, DREAL ARA',
                'autres_contributeurs': 'ASTERS, LPO Haute-Savoie',
                'date_avis_csrpn': date(2018, 6, 20),
                'organismes_redacteurs_lookup': ['Réserves Naturelles'],
                'commentaire': 'Plan de gestion en vigueur. Évaluation finale positive. '
                               'Enjeux centrés sur les pelouses alpines, la faune '
                               'de haute montagne et la maîtrise de la fréquentation.',
                'sites': [sites[1]],
                'membres': [
                    (users[1], True),   # admin.rnf - referent
                    (users[0], False),  # super_admin - membre simple
                ]
            },
            # Plan Grand-Voyeux: admin.cen referent, user.cen membre.
            # #277 — Brouillon en cours de workflow CSRPN (validation_step=avis_csrpn).
            # Site = RNR → non-RNN, bypass arrête après comité.
            {
                'nom': 'Plan de gestion 2022-2032 - Grand-Voyeux',
                'annee_debut': 2022,
                'annee_fin': 2032,
                'statut': 'draft',
                'validation_step': 'avis_csrpn',
                'version': '1',
                'gestion_partagee': False,
                'ct88': False,
                'risque_incendie': False,
                'id_evaluation': None,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'CEN Auvergne-Rhône-Alpes',
                'commentaire': 'Plan envoyé au CSRPN pour avis. Site RNR — pas '
                               'd\'arrêté préfectoral après validation comité (#277).',
                'sites': [sites[2]],
                'membres': [
                    (users[2], True),   # admin.cen - referent
                    (users[6], False),  # user.cen - membre
                ]
            },
            # Plan Vercors-Écrins: referent.vercors et admin.cen référents, user.cen membre
            {
                'nom': 'Plan de gestion inter-sites Vercors-Écrins 2021-2031',
                'annee_debut': 2021,
                'annee_fin': 2031,
                'statut': 'valide',
                'version': '2',
                'gestion_partagee': True,
                'ct88': True,
                'risque_incendie': True,
                'id_evaluation': eval_int,
                'id_redacteur_type': redac_be,
                'redacteur_nom': 'DREAL Auvergne-Rhône-Alpes',
                'commentaire': 'Plan de gestion partagé entre le PNR du Vercors et le Parc des Écrins',
                'sites': [sites[3], sites[5]],  # Vercors + Scandola
                'membres': [
                    (users[4], True),   # referent.vercors - referent
                    (users[2], True),   # admin.cen - referent
                    (users[6], False),  # user.cen - membre
                ]
            },
            # Plan Brouage: archive sans membres
            {
                'nom': 'Plan de gestion 2019-2029 - Marais de Brouage',
                'annee_debut': 2019,
                'annee_fin': 2029,
                'statut': 'archive',
                'version': '1',
                'gestion_partagee': False,
                'ct88': False,
                'risque_incendie': False,
                'id_evaluation': eval_fin,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'DREAL Nouvelle-Aquitaine',
                'commentaire': 'Plan archivé - nouvelle version en préparation',
                'sites': [sites[4]],
                'membres': []
            },
            # Plan Lac de Remoray + Grand-Voyeux: super_admin referent, admin.rnf membre
            {
                'nom': 'Plan de gestion 2023-2033 - Lacs et zones humides continentales',
                'annee_debut': 2023,
                'annee_fin': 2033,
                'rang': 3,
                'surface': 286,
                'statut': 'draft',
                'version': '1',
                'gestion_partagee': True,
                'ct88': True,
                'risque_incendie': False,
                'id_evaluation': None,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'RNF - Équipe Franche-Comté',
                'redacteurs': 'Sophie Moreau, Pierre Leclerc (DREAL BFC)',
                'relecteurs': 'CSRPN Bourgogne-Franche-Comté',
                'commentaire': 'Nouveau plan en cours de finalisation. '
                               'Enjeux principaux : qualité des eaux du lac, '
                               'tourbières et prairies humides, balbuzard pêcheur, '
                               'gestion des espèces exotiques envahissantes.',
                'sites': [sites[6], sites[2]],  # Lac de Remoray + Grand-Voyeux
                'membres': [
                    (users[0], True),   # super_admin - referent
                    (users[1], False),  # admin.rnf - membre simple
                    (users[5], False),  # user.rnf - membre simple
                    (users[3], True),   # referent.camargue - referent (E2E #292 cluster 1)
                    (users[6], False),  # user.cen - membre simple
                ]
            },
            # Plans archives
            {
                'nom': 'Plan de gestion 2010-2020 - Camargue et Brouage (ancien)',
                'annee_debut': 2010,
                'annee_fin': 2020,
                'rang': 2,
                'surface': 13117,
                'statut': 'archive',
                'version': '3',
                'gestion_partagee': True,
                'ct88': True,
                'risque_incendie': True,
                'id_evaluation': eval_fin,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'RNF - Équipe Camargue',
                'redacteurs': 'P. Grillas, A. Crivelli (Tour du Valat / RNF)',
                'relecteurs': 'CSRPN PACA',
                'date_avis_csrpn': date(2010, 1, 10),
                'commentaire': 'Ancien plan terminé, remplacé par le plan 2020-2030. '
                               'Évaluation finale réalisée en 2019.',
                'sites': [sites[0], sites[4]],  # Camargue + Marais de Brouage
                'membres': []
            },
            {
                'nom': 'Plan de gestion 2008-2018 - Aiguilles Rouges (ancien)',
                'annee_debut': 2008,
                'annee_fin': 2018,
                'rang': 1,
                'surface': 3279,
                'statut': 'archive',
                'version': '1',
                'gestion_partagee': False,
                'ct88': False,
                'risque_incendie': False,
                'id_evaluation': eval_fin,
                'id_redacteur_type': redac_be,
                'redacteur_nom': 'Bureau Natura 2000',
                'redacteurs': 'Bureau Natura 2000 (D. Petit)',
                'relecteurs': 'CSRPN Rhône-Alpes',
                'date_avis_csrpn': date(2008, 9, 5),
                'commentaire': 'Plan archivé suite à la mise en place du nouveau plan 2018-2028. '
                               '1er plan de gestion de la réserve.',
                'sites': [sites[1]],
                'membres': []
            },
            # #250 — Plan validé ET étendu (+2 ans). Extension = attribut
            # orthogonal au statut : le plan reste 'valide' (verrouillé en
            # lecture seule), seul `annees_extension` indique la prolongation.
            {
                'nom': 'Plan de gestion 2016-2025 - Scandola (étendu)',
                'annee_debut': 2016,
                'annee_fin': 2025,
                'rang': 2,
                'surface': 1669,
                'statut': 'valide',
                'annees_extension': 2,
                'version': '1',
                'gestion_partagee': False,
                'ct88': False,
                'risque_incendie': True,
                'id_evaluation': eval_int,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'RNF - Équipe Corse',
                'redacteurs': 'A. Aboucaya (RNF)',
                'relecteurs': 'CSRPN Corse',
                'date_avis_csrpn': date(2016, 6, 30),
                'commentaire': 'Plan validé prolongé de 2 ans (2025 → 2027) pendant la rédaction '
                               'du rang suivant. Le plan reste en lecture seule — '
                               'l\'extension est un attribut indépendant du statut (#250).',
                'sites': [sites[5]],  # Scandola
                'membres': [
                    (users[0], True),  # admin (super_admin) - référent
                    (users[1], True),  # admin.rnf - référent
                ]
            },
            # #250 — Plan validé dans la fenêtre de déclenchement de l'extension
            # (annee_fin = 2026, fenêtre [2025, 2028] → bouton « Étendre » visible)
            {
                'nom': 'Plan de gestion 2017-2026 - Lac de Remoray (à étendre)',
                'annee_debut': 2017,
                'annee_fin': 2026,
                'rang': 1,
                'surface': 286,
                'statut': 'valide',
                'version': '1',
                'gestion_partagee': False,
                'ct88': True,
                'risque_incendie': False,
                'id_evaluation': eval_int,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'RNF - Équipe Franche-Comté',
                'redacteurs': 'A. Magny (RNF), équipe Remoray',
                'relecteurs': 'CSRPN Bourgogne-Franche-Comté',
                'date_avis_csrpn': date(2017, 4, 12),
                'commentaire': 'Plan en fin de cycle. Le rang 2 est en cours de rédaction — '
                               'le bouton « Étendre la durée du plan » est disponible (#250).',
                'sites': [sites[6]],  # Lac de Remoray
                'membres': [
                    (users[0], True),  # admin (super_admin) - référent
                    (users[1], True),  # admin.rnf - référent
                ]
            },
        ]

        # Plans supplementaires sur des sites RNF sans membres directs
        # (utiles pour tester "Demander l'acces")
        # Plan sur Camargue (sites[0]) : admin est lie au site → test acces direct
        plans.append({
            'nom': 'Plan complémentaire 2024-2034 - Littoral et zones humides',
            'annee_debut': 2024,
            'annee_fin': 2034,
            'rang': 1,
            'surface': 5000,
            'statut': 'valide',
            'version': '1',
            'gestion_partagee': True,
            'ct88': False,
            'risque_incendie': False,
            'id_evaluation': eval_int,
            'id_redacteur_type': redac_gest,
            'redacteur_nom': 'RNF - Équipe Camargue',
            'commentaire': 'Plan complémentaire pour les zones humides et littorales. '
                           'Sans membres directs, pour tester la demande d\'accès.',
            'sites': [sites[0], sites[5]],  # Camargue + Scandola
            'membres': []
        })
        # Plan sur Lac de Remoray (sites[6]) : admin n'est PAS lie au site → test acces combine
        plans.append({
            'nom': 'Plan de gestion 2025-2035 - Lac de Remoray phase 2',
            'annee_debut': 2025,
            'annee_fin': 2035,
            'rang': 1,
            'surface': 286,
            'statut': 'draft',
            'version': '1',
            'gestion_partagee': False,
            'ct88': False,
            'risque_incendie': False,
            'id_evaluation': None,
            'id_redacteur_type': redac_gest,
            'redacteur_nom': 'RNF - Équipe Franche-Comté',
            'commentaire': 'Plan en préparation pour la phase 2 du Lac de Remoray. '
                           'Sans membres directs, pour tester la demande d\'accès combinée.',
            'sites': [sites[6]],  # Lac de Remoray
            'membres': []
        })
        # #277 — Brouillon en cours de workflow CSRPN, étape `comite_consultatif`
        # sur une RNN (Aiguilles Rouges) pour tester l'étape arrêté préfectoral.
        plans.append({
            'nom': 'Plan de gestion 2027-2037 - Aiguilles Rouges (workflow CSRPN)',
            'annee_debut': 2027,
            'annee_fin': 2037,
            'rang': 3,
            'surface': 3279,
            'statut': 'draft',
            'validation_step': 'comite_consultatif',
            'version': '1',
            'gestion_partagee': False,
            'ct88': False,
            'risque_incendie': False,
            'date_avis_csrpn': date(2026, 9, 18),
            'id_evaluation': None,
            'id_redacteur_type': redac_be,
            'redacteur_nom': 'Cabinet Natura Consulting',
            'commentaire': 'Avis CSRPN rendu, en attente de validation par le '
                           'comité consultatif. Site RNN → étape arrêté préfectoral '
                           'requise après validation (#277).',
            'sites': [sites[1]],  # Aiguilles Rouges (RNN)
            'membres': [
                (users[1], True),  # admin.rnf - referent
                (users[0], False), # super_admin - membre
            ],
        })

        # #278 — Chaîne de cohabitation Vercors : un plan validé est marqué
        # « en cours de révision » (attribut `en_revision=True`, statut reste
        # `valide`) ET étendu de 1 an. Le rang suivant est rédigé en brouillon
        # en parallèle. La révision peut être déclenchée avant ou après le
        # dépassement de `annee_fin` — pas de contrainte temporelle.
        plans.append({
            'nom': 'Plan de gestion 2014-2024 - Vercors (en cours de révision)',
            'annee_debut': 2014,
            'annee_fin': 2024,
            'rang': 1,
            'surface': 4500,
            'statut': 'valide',
            'en_revision': True,
            'annees_extension': 1,
            'version': '1',
            'gestion_partagee': False,
            'ct88': True,
            'risque_incendie': True,
            'id_evaluation': eval_fin,
            'id_redacteur_type': redac_gest,
            'redacteur_nom': 'CEN Auvergne-Rhône-Alpes',
            'redacteurs': 'L. Dupuis (CEN ARA)',
            'relecteurs': 'CSRPN Auvergne-Rhône-Alpes',
            'date_avis_csrpn': date(2014, 4, 22),
            'commentaire': 'Plan validé en fin de cycle, marqué en révision : il reste '
                           'fonctionnellement validé pendant que le rang suivant est '
                           'rédigé en brouillon. Prolongé de 1 an pour assurer la '
                           'transition. Démontre la cohabitation `en_revision` + extension '
                           '(#250 / #278). Le lien `next_rang_plan` est posé en fin de seed.',
            'sites': [sites[3]],  # Vercors
            # admin@test.fr inclus comme membre pour que le plan soit visible
            # dans « Mes plans » du super_admin par défaut (scope='mine').
            'membres': [
                (users[4], True),  # referent.vercors - referent
                (users[2], True),  # admin.cen - referent
                (users[6], False), # user.cen - membre
                (users[0], False), # super_admin - membre simple
            ],
        })
        plans.append({
            'nom': 'Plan de gestion 2026-2036 - Vercors (rang suivant en préparation)',
            'annee_debut': 2026,
            'annee_fin': 2036,
            'rang': 2,
            'surface': 4500,
            'statut': 'draft',
            'version': '2',
            'gestion_partagee': False,
            'ct88': True,
            'risque_incendie': True,
            'id_evaluation': None,
            'id_redacteur_type': redac_gest,
            'redacteur_nom': 'CEN Auvergne-Rhône-Alpes',
            'commentaire': 'Brouillon du rang 2 en cours de rédaction. Cohabite avec '
                           'le rang 1 « en cours de révision » jusqu\'à sa validation.',
            'sites': [sites[3]],  # Vercors
            'membres': [
                (users[4], True),  # referent.vercors - referent
                (users[2], True),  # admin.cen - referent
                (users[0], False), # super_admin - membre simple
            ],
        })

        # #281 — Panel libellés contextualisés du badge d'extension.
        # Plans validés + étendus sur sites de types différents pour
        # tester les libellés : RNN/RNR → "Plan prolongé", PNR → "Plan en
        # renouvellement", ENS/ENSD → "Plan étendu", autre → "Étendu".
        # admin@test.fr est référent pour visibilité par défaut.

        # Cas RNR — Grand-Voyeux : "Plan prolongé"
        plans.append({
            'nom': 'Plan de gestion 2015-2024 - Grand-Voyeux (RNR étendu)',
            'annee_debut': 2015,
            'annee_fin': 2024,
            'rang': 1,
            'statut': 'valide',
            'annees_extension': 1,
            'version': '1',
            'gestion_partagee': False,
            'ct88': False,
            'risque_incendie': False,
            'id_evaluation': eval_fin,
            'id_redacteur_type': redac_gest,
            'redacteur_nom': 'CEN Auvergne-Rhône-Alpes',
            'date_avis_csrpn': date(2015, 4, 8),
            'commentaire': 'Site RNR → badge contextualisé « Plan prolongé » (#281). '
                           'Plan validé étendu de 1 an.',
            'sites': [sites[2]],  # Grand-Voyeux (RNR)
            'membres': [
                (users[0], True),  # super_admin - referent
                (users[2], True),  # admin.cen - referent
            ],
        })

        # Cas ENS — Marais de Brouage : "Plan étendu"
        plans.append({
            'nom': 'Plan de gestion 2014-2023 - Marais de Brouage (ENS étendu)',
            'annee_debut': 2014,
            'annee_fin': 2023,
            'rang': 1,
            'statut': 'valide',
            'annees_extension': 2,
            'version': '1',
            'gestion_partagee': False,
            'ct88': False,
            'risque_incendie': False,
            'id_evaluation': eval_fin,
            'id_redacteur_type': redac_gest,
            'redacteur_nom': 'DREAL Nouvelle-Aquitaine',
            'date_avis_csrpn': date(2014, 6, 16),
            'commentaire': 'Site ENS → badge contextualisé « Plan étendu » (#281). '
                           'Plan validé étendu de 2 ans.',
            'sites': [sites[4]],  # Marais de Brouage (ENS)
            'membres': [
                (users[0], True),  # super_admin - referent
            ],
        })

        return plans

    def _renumber_versions_per_rang(self) -> None:
        """Renumérote les versions de chaque chaîne plan_parent par rang.

        Un changement de rang correspond à un NOUVEAU plan de gestion : la
        version repart à v1. Les versions hardcodées dans les seeds sont
        normalisées ici pour cohérence avec la règle métier (#ND) et avec
        la migration `0074_renumber_versions_per_rang`.
        """
        roots = PlanGestion.objects.filter(plan_parent__isnull=True)
        visited = set()
        for root in roots:
            if root.pk in visited:
                continue
            # BFS de la chaîne complète
            chain = []
            queue = [root]
            local_visited = set()
            while queue:
                current = queue.pop(0)
                if current.pk in local_visited:
                    continue
                local_visited.add(current.pk)
                chain.append(current)
                for child in PlanGestion.objects.filter(
                    plan_parent_id=current.pk
                ).order_by('date_ajout'):
                    queue.append(child)
            visited.update(p.pk for p in chain)

            # Grouper par rang, trier chronologiquement, renuméroter
            by_rang = {}
            for plan in chain:
                by_rang.setdefault(plan.rang or 1, []).append(plan)
            for rang, plans_in_rang in by_rang.items():
                plans_in_rang.sort(key=lambda p: p.date_ajout or p.pk)
                for idx, plan in enumerate(plans_in_rang, start=1):
                    new_version = str(idx)
                    if plan.version != new_version:
                        plan.version = new_version
                        plan.save(update_fields=['version'])

    def _set_plan_membres(self, plan: PlanGestion, membres: list) -> None:
        """Synchronise les membres CorRolePlan et le M2M referents pour un plan."""
        referents_list = []
        for user, is_referent in membres:
            CorRolePlan.objects.update_or_create(
                id_role=user,
                plan_de_gestion=plan,
                defaults={'referent': is_referent}
            )
            if is_referent:
                referents_list.append(user)
        plan.referents.set(referents_list)

    def _seed_sandbox(self, admin, sites, doc_types) -> List[PlanGestion]:
        """#348 — « Bac à sable » : chaîne dédiée aux tests de SUPPRESSION et de
        DUPLICATION de versions, sans impacter les autres jeux de données.

        Chaîne (plans tous préfixés « Bac à sable — ») :
          Rang 1 : v1 (validé, racine, AVEC enjeux) → v2 (modifié)
                   → v3 (éval mi-parcours : modifié + is_mi_parcours)
          Rang 2 : brouillon — pour observer la renumérotation multi-rangs.

        Permet de tester : suppression début/milieu/fin de chaîne, cascade du
        contenu (enjeux) et des liens, renumérotation par rang, et duplication
        d'une version validée. `reset()` les supprime (delete sur tous les plans).
        """
        plan_initial, eval_mi, plan_revise = doc_types
        site = sites[0] if sites else None
        referent = admin
        created: List[PlanGestion] = []

        def _mk(nom, statut, version, rang, parent, doc_type,
                annee_debut, annee_fin, is_mi_parcours=False):
            plan, _ = PlanGestion.objects.update_or_create(
                nom=nom,
                defaults={
                    'statut': statut,
                    'version': version,
                    'rang': rang,
                    'plan_parent': parent,
                    'id_type_document': doc_type,
                    'annee_debut': annee_debut,
                    'annee_fin': annee_fin,
                    'is_mi_parcours': is_mi_parcours,
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                },
            )
            if site:
                CorSitePg.objects.get_or_create(
                    site=site, plan_de_gestion=plan, defaults={'rang': 1}
                )
            CorRolePlan.objects.update_or_create(
                id_role=referent, plan_de_gestion=plan, defaults={'referent': True}
            )
            plan.referents.add(referent)
            created.append(plan)
            return plan

        v1 = _mk('Bac à sable — Plan initial 2010-2020', 'valide', '1', 1, None,
                 plan_initial, 2010, 2020)
        v2 = _mk('Bac à sable — Plan révisé 2020-2030', 'modifie', '2', 1, v1,
                 plan_revise, 2020, 2030)
        v3 = _mk('Bac à sable — Éval mi-parcours 2025', 'modifie', '3', 1, v2,
                 eval_mi, 2025, 2025, is_mi_parcours=True)
        _mk('Bac à sable — Plan rang 2 (brouillon) 2030-2040', 'draft', '1', 2, v3,
            plan_revise, 2030, 2040)

        # Contenu sur la racine : permet de vérifier la cascade à la suppression.
        self._seed_sandbox_enjeux(v1, admin)

        self.log_item(
            'chain',
            'Bac à sable (#348) : rang1 v1→v2→v3(mi-parcours) + rang2 brouillon (avec enjeux)'
        )
        return created

    def _seed_sandbox_enjeux(self, plan: PlanGestion, admin) -> None:
        """Quelques enjeux de démonstration sur le plan racine du bac à sable."""
        from apps.plans.models_enjeux import Enjeu

        cat = Nomenclature.objects.filter(
            id_type__mnemonique='CATEGORIE_ENJEU', mnemonique='ENJEU'
        ).first()
        if not cat:
            return
        prio = Nomenclature.objects.filter(
            id_type__mnemonique='IMPORTANCE_ENJEU', mnemonique='PRIORITE_1'
        ).first()

        demos = [
            ('Bac à sable — Enjeu de démonstration A', 'Démo A'),
            ('Bac à sable — Enjeu de démonstration B', 'Démo B'),
        ]
        for rang, (libelle, court) in enumerate(demos, start=1):
            Enjeu.objects.update_or_create(
                id_pg=plan,
                libelle=libelle,
                defaults={
                    'id_categorie': cat,
                    'intitule_court': court,
                    'rang': rang,
                    'id_importance': prio,
                    'categorie_ecologique': True,
                    'habitat': True,
                    'description': "Enjeu de test pour vérifier la cascade lors de la "
                                   "suppression d'une version (#348).",
                    'id_utilisateur_ajout': admin,
                },
            )

    def seed(self) -> List[PlanGestion]:
        """
        Crée les plans de gestion de test.

        Returns:
            Liste des plans créés
        """
        self.log_header('Création des plans de gestion')

        users = self.context.require('users')
        sites = self.context.require('sites')
        organismes = self.context.get('organismes', [])

        admin = users[0]  # Pour id_utilisateur_ajout
        plans_data = self._get_plans_data(users, sites)

        # Récupérer les organismes par nom pour les organismes rédacteurs
        from apps.users.models import BibOrganismes
        org_cen = BibOrganismes.objects.filter(nom_organisme__icontains='CEN').first()
        org_rnf = BibOrganismes.objects.filter(nom_organisme__icontains='Réserves Naturelles').first()

        plans = []
        for plan_data in plans_data:
            plan_sites = plan_data.pop('sites')
            plan_membres = plan_data.pop('membres')
            redacteur_config = plan_data.pop('organismes_redacteurs_lookup', [])

            plan, created = PlanGestion.objects.update_or_create(
                nom=plan_data['nom'],
                defaults={
                    **plan_data,
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin
                }
            )

            # Lier aux sites
            for i, site in enumerate(plan_sites):
                CorSitePg.objects.get_or_create(
                    site=site,
                    plan_de_gestion=plan,
                    defaults={'rang': i + 1}
                )

            # Ajouter les membres et referents via CorRolePlan
            referents_list = []
            for user, is_referent in plan_membres:
                CorRolePlan.objects.update_or_create(
                    id_role=user,
                    plan_de_gestion=plan,
                    defaults={'referent': is_referent}
                )
                if is_referent:
                    referents_list.append(user)

            # Aussi mettre à jour le ManyToMany referents pour compatibilité
            plan.referents.set(referents_list)

            # Ajouter les organismes rédacteurs pour certains plans
            redacteur_lookups = redacteur_config
            redacteur_orgs = []
            for lookup in redacteur_lookups:
                org = BibOrganismes.objects.filter(nom_organisme__icontains=lookup).first()
                if org:
                    from apps.plans.models import CorRedacteurPlan
                    CorRedacteurPlan.objects.get_or_create(
                        plan_de_gestion=plan,
                        uuid_og=org
                    )
                    redacteur_orgs.append(org)

            plans.append(plan)
            status = "créé" if created else "mis à jour"
            sites_names = ", ".join([s.nom_site[:20] for s in plan_sites])
            membres_count = len(plan_membres)
            referents_count = len(referents_list)
            redacteur_count = len(redacteur_orgs)
            self.log_item(status, f"{plan.nom[:50]}... ({plan.statut})")
            if self.verbosity >= 2:
                self.stdout.write(f"              Sites: {sites_names}")
                self.stdout.write(f"              Membres: {membres_count} (dont {referents_count} référents)")
                if redacteur_count:
                    self.stdout.write(f"              Organismes rédacteurs: {redacteur_count}")

        # =====================================================================
        # Chaînes de versions complètes
        # =====================================================================
        plan_initial_type = Nomenclature.objects.filter(mnemonique='PLAN_INITIAL').first()
        eval_mi_type = Nomenclature.objects.filter(mnemonique='EVAL_MI_PARCOURS').first()
        plan_revise_type = Nomenclature.objects.filter(mnemonique='PLAN_REVISE').first()

        if not (plan_initial_type and eval_mi_type and plan_revise_type):
            self.log_item('skip', 'Nomenclatures Type document plan manquantes, chaînes de versions ignorées')
        else:
            self.stdout.write('')
            self.log_header('Chaînes de versions')

            # -----------------------------------------------------------------
            # Chaîne Camargue (5 niveaux) — la plus complète
            # Plan initial 2000-2010 (archive) → Eval mi-parcours (archive)
            # → Plan révisé 2010-2020 (archive, index 6) → Plan actuel 2020-2030 (valide, index 0)
            # → Eval mi-parcours en cours (draft)
            # -----------------------------------------------------------------

            # Noeud racine : Plan initial 2000-2010
            camargue_root, _ = PlanGestion.objects.update_or_create(
                nom='Plan de gestion 2000-2010 - Camargue (plan initial)',
                defaults={
                    'plan_parent': None,
                    'id_type_document': plan_initial_type,
                    'statut': 'archive',
                    'version': '1',
                    'annee_debut': 2000,
                    'annee_fin': 2010,
                    'rang': 1,
                    'surface': 13117,
                    'gestion_partagee': True,
                    'ct88': True,
                    'risque_incendie': True,
                    'id_evaluation': Nomenclature.objects.filter(mnemonique='Finale').first(),
                    'id_redacteur_type': Nomenclature.objects.filter(mnemonique='OG').first(),
                    'redacteur_nom': 'RNF - Équipe historique Camargue',
                    'redacteurs': 'L. Hoffmann, P. Grillas (Tour du Valat)',
                    'relecteurs': 'CSRPN PACA',
                    'date_avis_csrpn': date(2000, 5, 12),
                    'commentaire': 'Premier plan de gestion de la Réserve de Camargue. '
                                   'Diagnostic initial et premières orientations de gestion.',
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                }
            )
            for s in [sites[0], sites[4]]:
                CorSitePg.objects.get_or_create(site=s, plan_de_gestion=camargue_root, defaults={'rang': 1})
            plans.append(camargue_root)

            # Eval mi-parcours du plan initial (archivée)
            camargue_eval1, _ = PlanGestion.objects.update_or_create(
                nom='Évaluation mi-parcours 2005 - Camargue',
                defaults={
                    'plan_parent': camargue_root,
                    'id_type_document': eval_mi_type,
                    'statut': 'archive',
                    'version': '2',
                    'annee_debut': 2000,
                    'annee_fin': 2010,
                    'rang': 1,
                    'surface': 13117,
                    'gestion_partagee': True,
                    'ct88': True,
                    'risque_incendie': True,
                    'id_evaluation': Nomenclature.objects.filter(mnemonique='Intermédiaire').first(),
                    'id_redacteur_type': Nomenclature.objects.filter(mnemonique='OG').first(),
                    'redacteur_nom': 'RNF - Équipe Camargue',
                    'commentaire': 'Évaluation à mi-parcours du plan 2000-2010. '
                                   'Bilan positif sur la gestion hydraulique, '
                                   'ajustements nécessaires sur le volet fréquentation.',
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                }
            )
            for s in [sites[0], sites[4]]:
                CorSitePg.objects.get_or_create(site=s, plan_de_gestion=camargue_eval1, defaults={'rang': 1})
            plans.append(camargue_eval1)

            # Relier le plan révisé 2010-2020 (index 6) au plan initial
            plans[6].plan_parent = camargue_eval1
            plans[6].id_type_document = plan_revise_type
            plans[6].version = '3'
            plans[6].save(update_fields=['plan_parent', 'id_type_document', 'version'])

            # Relier le plan actuel 2020-2030 (index 0) au plan révisé 2010-2020
            plans[0].plan_parent = plans[6]
            plans[0].id_type_document = plan_revise_type
            plans[0].version = '4'
            plans[0].save(update_fields=['plan_parent', 'id_type_document', 'version'])

            # Eval mi-parcours du plan actuel (en cours, draft)
            camargue_eval2, _ = PlanGestion.objects.update_or_create(
                nom='Évaluation mi-parcours 2025 - Camargue (brouillon E2E)',
                defaults={
                    'plan_parent': plans[0],
                    'id_type_document': eval_mi_type,
                    'statut': 'draft',
                    'version': '5',
                    'annee_debut': 2020,
                    'annee_fin': 2030,
                    'rang': 3,
                    'surface': 13117,
                    'gestion_partagee': True,
                    'ct88': True,
                    'risque_incendie': True,
                    'id_redacteur_type': Nomenclature.objects.filter(mnemonique='OG').first(),
                    'redacteur_nom': 'RNF - Équipe Camargue',
                    'commentaire': 'Évaluation mi-parcours en cours de rédaction. '
                                   'Premiers résultats encourageants sur la restauration '
                                   'des habitats humides.',
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                }
            )
            for s in [sites[0], sites[4]]:
                CorSitePg.objects.get_or_create(site=s, plan_de_gestion=camargue_eval2, defaults={'rang': 1})
            # Hériter les membres du plan parent + ajouter des membres supplémentaires
            self._set_plan_membres(camargue_eval2, [
                (users[0], True),   # super_admin - referent
                (users[3], True),   # referent.camargue - referent
                (users[1], False),  # admin.rnf - membre
                (users[5], False),  # user.rnf - membre
                (users[7], False),  # test@example.com - membre
                (users[4], False),  # referent.vercors - membre
            ])
            plans.append(camargue_eval2)

            self.log_item('chain', 'Camargue: 5 niveaux (initial → eval → révisé → actuel → eval)')

            # -----------------------------------------------------------------
            # Chaîne Aiguilles Rouges (4 niveaux)
            # Plan initial 2008-2018 (archive, index 7) → Plan 2018-2028 (valide, index 1)
            # → Eval mi-parcours (valide) → Plan révisé (draft)
            # -----------------------------------------------------------------

            # Relier le plan initial (index 7)
            plans[7].id_type_document = plan_initial_type
            plans[7].version = '1'
            plans[7].save(update_fields=['id_type_document', 'version'])

            # Relier le plan actuel (index 1) au plan initial.
            # #275 — Bien qu'il succède à un plan archivé, c'est la première
            # version de son propre rang (rang 2). Le statut `modifie` est
            # réservé aux modifications **intra-rang** : on reste donc en
            # `valide` (déjà défini dans le dict initial du plan).
            plans[1].plan_parent = plans[7]
            plans[1].id_type_document = plan_revise_type
            plans[1].version = '2'
            plans[1].save(update_fields=['plan_parent', 'id_type_document', 'version'])

            # Eval mi-parcours (validée — l'évaluation a été terminée).
            # #276 — Cette modification a été déclarée comme évaluation mi-parcours :
            # statut=`modifie` + drapeau `is_mi_parcours=True` (unique par chaîne).
            ar_eval, _ = PlanGestion.objects.update_or_create(
                nom='Évaluation mi-parcours 2023 - Aiguilles Rouges',
                defaults={
                    'plan_parent': plans[1],
                    'id_type_document': eval_mi_type,
                    'statut': 'modifie',
                    'is_mi_parcours': True,
                    'version': '3',
                    'annee_debut': 2018,
                    'annee_fin': 2028,
                    'rang': 2,
                    'surface': 3279,
                    'gestion_partagee': False,
                    'ct88': False,
                    'risque_incendie': False,
                    'id_evaluation': Nomenclature.objects.filter(mnemonique='Intermédiaire').first(),
                    'id_redacteur_type': Nomenclature.objects.filter(mnemonique='BE').first(),
                    'redacteur_nom': 'Cabinet Natura Consulting',
                    'date_avis_csrpn': date(2023, 11, 15),
                    'commentaire': 'Évaluation mi-parcours validée. Bilan globalement positif. '
                                   'Recommandations de renforcer le suivi du gypaète barbu '
                                   'et de mieux encadrer la fréquentation estivale. '
                                   'Statut "modifié" + drapeau is_mi_parcours=True (#276).',
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                }
            )
            for cor_site in plans[1].sites.all():
                CorSitePg.objects.get_or_create(site=cor_site.site, plan_de_gestion=ar_eval, defaults={'rang': cor_site.rang})
            # Hériter les membres du plan parent
            self._set_plan_membres(ar_eval, [
                (users[1], True),   # admin.rnf - referent
                (users[0], False),  # super_admin - membre
            ])
            plans.append(ar_eval)

            # Plan révisé suite à l'évaluation (en cours de rédaction)
            ar_revise, _ = PlanGestion.objects.update_or_create(
                nom='Plan de gestion révisé 2018-2028 - Aiguilles Rouges',
                defaults={
                    'plan_parent': ar_eval,
                    'id_type_document': plan_revise_type,
                    'statut': 'draft',
                    'version': '4',
                    'annee_debut': 2018,
                    'annee_fin': 2028,
                    'rang': 2,
                    'surface': 3279,
                    'gestion_partagee': False,
                    'ct88': False,
                    'risque_incendie': False,
                    'id_redacteur_type': Nomenclature.objects.filter(mnemonique='BE').first(),
                    'redacteur_nom': 'Cabinet Natura Consulting',
                    'commentaire': 'Révision du plan suite à l\'évaluation mi-parcours. '
                                   'Intègre les nouvelles orientations : renforcement du suivi '
                                   'du gypaète, création d\'un zonage de quiétude estivale.',
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                }
            )
            for cor_site in plans[1].sites.all():
                CorSitePg.objects.get_or_create(site=cor_site.site, plan_de_gestion=ar_revise, defaults={'rang': cor_site.rang})
            # Hériter les membres du plan parent + ajouter user.rnf comme membre
            self._set_plan_membres(ar_revise, [
                (users[1], True),   # admin.rnf - referent
                (users[0], False),  # super_admin - membre
                (users[5], False),  # user.rnf - membre
            ])
            plans.append(ar_revise)

            self.log_item('chain', 'Aiguilles Rouges: 4 niveaux (initial → révisé → eval → révisé)')

            # -----------------------------------------------------------------
            # Chaîne Vercors-Écrins (3 niveaux)
            # Plan initial 2011-2021 (archive) → Plan actuel 2021-2031 (valide, index 3)
            # → Eval mi-parcours (draft)
            # -----------------------------------------------------------------

            vercors_root, _ = PlanGestion.objects.update_or_create(
                nom='Plan de gestion 2011-2021 - Vercors-Écrins (plan initial)',
                defaults={
                    'plan_parent': None,
                    'id_type_document': plan_initial_type,
                    'statut': 'archive',
                    'version': '1',
                    'annee_debut': 2011,
                    'annee_fin': 2021,
                    'rang': 1,
                    'surface': plans[3].surface if plans[3].surface else None,
                    'gestion_partagee': True,
                    'ct88': True,
                    'risque_incendie': True,
                    'id_evaluation': Nomenclature.objects.filter(mnemonique='Finale').first(),
                    'id_redacteur_type': Nomenclature.objects.filter(mnemonique='BE').first(),
                    'redacteur_nom': 'DREAL Rhône-Alpes',
                    'date_avis_csrpn': date(2011, 3, 20),
                    'commentaire': 'Premier plan inter-sites couvrant le Vercors et les Écrins. '
                                   'Diagnostic partagé entre PNR et Parc National.',
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                }
            )
            for cor_site in plans[3].sites.all():
                CorSitePg.objects.get_or_create(site=cor_site.site, plan_de_gestion=vercors_root, defaults={'rang': cor_site.rang})
            plans.append(vercors_root)

            # Relier le plan actuel (index 3) au plan initial.
            # #275 — Plan révisé du PG initial archivé → statut `modifie`.
            plans[3].plan_parent = vercors_root
            plans[3].id_type_document = plan_revise_type
            plans[3].version = '2'
            plans[3].statut = 'modifie'
            plans[3].save(update_fields=['plan_parent', 'id_type_document', 'version', 'statut'])

            # Eval mi-parcours du plan actuel (draft)
            vercors_eval, _ = PlanGestion.objects.update_or_create(
                nom='Évaluation mi-parcours 2026 - Vercors-Écrins',
                defaults={
                    'plan_parent': plans[3],
                    'id_type_document': eval_mi_type,
                    'statut': 'draft',
                    'version': '3',
                    'annee_debut': 2021,
                    'annee_fin': 2031,
                    'rang': 1,
                    'gestion_partagee': True,
                    'ct88': True,
                    'risque_incendie': True,
                    'id_redacteur_type': Nomenclature.objects.filter(mnemonique='BE').first(),
                    'redacteur_nom': 'DREAL Auvergne-Rhône-Alpes',
                    'commentaire': 'Évaluation mi-parcours en préparation. '
                                   'Premiers retours terrain en cours de compilation.',
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                }
            )
            for cor_site in plans[3].sites.all():
                CorSitePg.objects.get_or_create(site=cor_site.site, plan_de_gestion=vercors_eval, defaults={'rang': cor_site.rang})
            # Hériter les membres du plan parent + ajouter user.cen comme membre
            self._set_plan_membres(vercors_eval, [
                (users[4], True),   # referent.vercors - referent
                (users[2], True),   # admin.cen - referent
                (users[6], False),  # user.cen - membre
            ])
            plans.append(vercors_eval)

            self.log_item('chain', 'Vercors-Écrins: 3 niveaux (initial → révisé → eval)')

            # -----------------------------------------------------------------
            # Chaîne « validé + en_revision ↔ brouillon » sur Vercors (#250 / #278)
            # Le rang 1 est validé ET marqué en cours de révision ET étendu d'1 an.
            # Le rang 2 est en brouillon en parallèle. Lien explicite via
            # `next_rang_plan` pour exposer « Voir le rang suivant » dans l'UI.
            # -----------------------------------------------------------------
            try:
                rang1 = PlanGestion.objects.get(
                    nom='Plan de gestion 2014-2024 - Vercors (en cours de révision)'
                )
                rang2 = PlanGestion.objects.get(
                    nom='Plan de gestion 2026-2036 - Vercors (rang suivant en préparation)'
                )
                rang1.id_type_document = plan_initial_type
                rang1.next_rang_plan = rang2
                rang1.save(update_fields=['id_type_document', 'next_rang_plan'])
                rang2.plan_parent = rang1
                rang2.id_type_document = plan_revise_type
                rang2.save(update_fields=['plan_parent', 'id_type_document'])
                self.log_item('chain', 'Vercors (revision/draft): validé+étendu+en_revision ↔ brouillon rang 2 (next_rang_plan posé)')
            except PlanGestion.DoesNotExist:
                pass

            # -----------------------------------------------------------------
            # Panel #276 — Variantes d'évaluations mi-parcours
            # Couvre tous les états d'une éval mi-parcours pour tester l'UI.
            # Plans déjà présents :
            #   - Camargue eval 2005 (archive, EVAL_MI_PARCOURS, historique)
            #   - Camargue eval 2025 (draft, EVAL_MI_PARCOURS)
            #   - Aiguilles Rouges eval 2023 (modifie + is_mi_parcours=True)
            #   - Vercors-Écrins eval 2026 (draft, EVAL_MI_PARCOURS)
            # Nouveaux ajouts ci-dessous : variantes CSRPN + cumul d'attributs.
            # -----------------------------------------------------------------

            # Cas (a) — EVAL_MI_PARCOURS en avis CSRPN sur Lac de Remoray (validé)
            try:
                lr_parent = PlanGestion.objects.filter(
                    nom__icontains='Lac de Remoray (à étendre)'
                ).first()
                if lr_parent:
                    lr_eval, _ = PlanGestion.objects.update_or_create(
                        nom='Évaluation mi-parcours 2022 - Lac de Remoray (avis CSRPN)',
                        defaults={
                            'plan_parent': lr_parent,
                            'id_type_document': eval_mi_type,
                            'statut': 'draft',
                            'validation_step': 'avis_csrpn',
                            'version': '2',
                            'annee_debut': 2017,
                            'annee_fin': 2026,
                            'rang': 1,
                            'gestion_partagee': False,
                            'ct88': True,
                            'risque_incendie': False,
                            'id_redacteur_type': Nomenclature.objects.filter(mnemonique='OG').first(),
                            'redacteur_nom': 'RNF - Équipe Franche-Comté',
                            'date_avis_csrpn': date(2022, 5, 14),
                            'commentaire': 'Évaluation mi-parcours envoyée au CSRPN pour avis. '
                                           'Workflow #277 → comite_consultatif puis validation '
                                           '→ modifie + is_mi_parcours=True (#276).',
                            'id_utilisateur_ajout': admin,
                            'id_utilisateur_maj': admin,
                        }
                    )
                    for cor_site in lr_parent.sites.all():
                        CorSitePg.objects.get_or_create(
                            site=cor_site.site, plan_de_gestion=lr_eval,
                            defaults={'rang': cor_site.rang},
                        )
                    self._set_plan_membres(lr_eval, [
                        (users[0], True),   # super_admin - referent
                        (users[1], True),   # admin.rnf - referent
                    ])
                    plans.append(lr_eval)
            except Exception:
                pass

            # Cas (b) — EVAL_MI_PARCOURS en validation comité sur Vercors 2014-2024
            # (le plan est validé+étendu+en_revision et n'a pas encore de mi-parcours
            # dans sa chaîne — donc on peut en ajouter une).
            try:
                vc_parent = PlanGestion.objects.filter(
                    nom__icontains='Vercors (en cours de révision)'
                ).first()
                if vc_parent:
                    vc_eval, _ = PlanGestion.objects.update_or_create(
                        nom='Évaluation mi-parcours 2020 - Vercors (validation comité)',
                        defaults={
                            'plan_parent': vc_parent,
                            'id_type_document': eval_mi_type,
                            'statut': 'draft',
                            'validation_step': 'comite_consultatif',
                            'version': '2',
                            'annee_debut': 2014,
                            'annee_fin': 2024,
                            'rang': 1,
                            'gestion_partagee': False,
                            'ct88': True,
                            'risque_incendie': True,
                            'id_redacteur_type': Nomenclature.objects.filter(mnemonique='OG').first(),
                            'redacteur_nom': 'CEN Auvergne-Rhône-Alpes',
                            'date_avis_csrpn': date(2020, 3, 12),
                            'commentaire': 'Avis CSRPN rendu, en attente de validation par le '
                                           'comité consultatif. À la validation finale → '
                                           'statut=modifie + is_mi_parcours=True.',
                            'id_utilisateur_ajout': admin,
                            'id_utilisateur_maj': admin,
                        }
                    )
                    for cor_site in vc_parent.sites.all():
                        CorSitePg.objects.get_or_create(
                            site=cor_site.site, plan_de_gestion=vc_eval,
                            defaults={'rang': cor_site.rang},
                        )
                    # admin@test.fr (users[0]) ajouté en référent pour que ce
                    # plan apparaisse dans « Mes plans » du super_admin par défaut.
                    self._set_plan_membres(vc_eval, [
                        (users[0], True),   # super_admin - referent
                        (users[4], True),   # referent.vercors - referent
                        (users[2], True),   # admin.cen - referent
                    ])
                    plans.append(vc_eval)
            except Exception:
                pass

            # Cas (c) — combiner is_mi_parcours + extension sur Aiguilles Rouges
            # (l'évaluation mi-parcours d'Aiguilles Rouges 2023 reçoit aussi
            # une extension d'1 an pour démontrer la cohabitation des 2 flags).
            try:
                ar_eval_existing = PlanGestion.objects.filter(
                    nom='Évaluation mi-parcours 2023 - Aiguilles Rouges'
                ).first()
                if ar_eval_existing:
                    ar_eval_existing.annees_extension = 1
                    ar_eval_existing.save(update_fields=['annees_extension'])
                    self.log_item('chain', 'Aiguilles Rouges eval 2023 : modifie + is_mi_parcours=True + étendu +1 an')
            except Exception:
                pass

            self.log_item('chain', 'Panel mi-parcours (#276) : 6 plans (draft, draft, avis_csrpn, comite, modifie+is_mi_parcours, archive)')

        # =====================================================================
        # Renumérotation des versions par rang (cohérence #ND)
        # Un rang = un autre plan de gestion, donc la version repart à v1
        # quand le rang change. On parcourt chaque chaîne et on renumérote.
        # =====================================================================
        self._renumber_versions_per_rang()

        # =====================================================================
        # Documents de test (fichiers attachés aux plans)
        # =====================================================================
        self.stdout.write('')
        self.log_header('Documents de test')

        fichiers_data = [
            # Plan Camargue (index 0) - 3 documents
            {
                'plan': plans[0],
                'nom_fichier': 'PdG_Camargue_2020-2030_Partie1.pdf',
                'type_fichier': 'document',
                'titre': 'PdG - Partie 1 : Diagnostic',
                'description': 'Diagnostic écologique et socio-économique de la réserve',
                'auteur': 'RNF - Équipe Camargue',
                'taille_fichier': 15_234_567,
                'extension': 'pdf',
                'date_document': date(2020, 3, 15),
                'public': True,
                'ordre_affichage': 1,
            },
            {
                'plan': plans[0],
                'nom_fichier': 'PdG_Camargue_2020-2030_Partie2.pdf',
                'type_fichier': 'document',
                'titre': 'PdG - Partie 2 : Plan d\'action',
                'description': 'Objectifs et actions de gestion',
                'auteur': 'RNF - Équipe Camargue',
                'taille_fichier': 8_456_789,
                'extension': 'pdf',
                'date_document': date(2020, 3, 15),
                'public': True,
                'ordre_affichage': 2,
            },
            {
                'plan': plans[0],
                'nom_fichier': 'Carte_habitats_Camargue.jpg',
                'type_fichier': 'carte',
                'titre': 'Carte des habitats',
                'description': 'Cartographie des habitats naturels de la réserve',
                'auteur': 'SIG Camargue',
                'taille_fichier': 3_210_456,
                'extension': 'jpg',
                'date_document': date(2019, 11, 20),
                'public': False,
                'ordre_affichage': 3,
            },
            # Plan Aiguilles Rouges (index 1) - 2 documents
            {
                'plan': plans[1],
                'nom_fichier': 'PdG_AiguillesRouges_2018-2028.pdf',
                'type_fichier': 'document',
                'titre': 'Plan de gestion intégré',
                'description': 'Document complet du plan de gestion',
                'auteur': 'Cabinet Natura Consulting',
                'taille_fichier': 22_345_678,
                'extension': 'pdf',
                'date_document': date(2018, 6, 20),
                'public': True,
                'ordre_affichage': 1,
            },
            {
                'plan': plans[1],
                'nom_fichier': 'Annexes_AiguillesRouges.pdf',
                'type_fichier': 'annexe',
                'titre': 'Annexes techniques',
                'description': 'Inventaires faunistiques et floristiques',
                'auteur': 'Cabinet Natura Consulting',
                'taille_fichier': 5_678_901,
                'extension': 'pdf',
                'date_document': date(2018, 6, 20),
                'public': False,
                'ordre_affichage': 2,
            },
            # Plan Lacs et zones humides continentales (index 5) - 3 documents
            {
                'plan': plans[5],
                'nom_fichier': 'PdG_Lacs_ZH_2023-2033_diagnostic.pdf',
                'type_fichier': 'document',
                'titre': 'Diagnostic écologique - Lacs et zones humides',
                'description': 'Diagnostic initial des lacs et tourbières du secteur Franche-Comté',
                'auteur': 'RNF - Équipe Franche-Comté',
                'taille_fichier': 18_765_432,
                'extension': 'pdf',
                'date_document': date(2023, 4, 12),
                'public': True,
                'ordre_affichage': 1,
            },
            {
                'plan': plans[5],
                'nom_fichier': 'Carte_tourbieres_Remoray.pdf',
                'type_fichier': 'carte',
                'titre': 'Cartographie des tourbières',
                'description': 'Localisation et état de conservation des tourbières autour du Lac de Remoray',
                'auteur': 'SIG DREAL BFC',
                'taille_fichier': 6_543_210,
                'extension': 'pdf',
                'date_document': date(2022, 9, 5),
                'public': False,
                'ordre_affichage': 2,
            },
            {
                'plan': plans[5],
                'nom_fichier': 'Inventaire_balbuzard_2024.xlsx',
                'type_fichier': 'annexe',
                'titre': 'Inventaire balbuzard pêcheur 2024',
                'description': 'Données de suivi du balbuzard pêcheur sur le Lac de Remoray',
                'auteur': 'Sophie Moreau (DREAL BFC)',
                'taille_fichier': 245_678,
                'extension': 'xlsx',
                'date_document': date(2024, 10, 30),
                'public': False,
                'ordre_affichage': 3,
            },
            # Plan Vercors-Ecrins (index 3) - 2 documents
            {
                'plan': plans[3],
                'nom_fichier': 'Rapport_evaluation_Vercors.pdf',
                'type_fichier': 'rapport',
                'titre': 'Rapport d\'évaluation à mi-parcours',
                'description': 'Bilan des 5 premières années de gestion',
                'auteur': 'DREAL Auvergne-Rhône-Alpes',
                'taille_fichier': 12_456_789,
                'extension': 'pdf',
                'date_document': date(2026, 1, 10),
                'public': True,
                'ordre_affichage': 1,
            },
            {
                'plan': plans[3],
                'nom_fichier': 'Photo_pelouses_alpines.jpg',
                'type_fichier': 'photo',
                'titre': 'Pelouses alpines du Vercors',
                'description': 'Suivi photographique des pelouses alpines',
                'auteur': 'PNR Vercors',
                'taille_fichier': 4_567_890,
                'extension': 'jpg',
                'date_document': date(2024, 7, 15),
                'public': False,
                'ordre_affichage': 2,
            },
        ]

        fichiers_count = 0
        for fdata in fichiers_data:
            plan_obj = fdata.pop('plan')
            # Get the first referent of the plan, or admin as fallback
            referents = plan_obj.referents.all()
            uploader = referents.first() if referents.exists() else admin

            # #372 — Écrire un binaire de démonstration sur le disque pour que
            # le téléchargement fonctionne (les seeders ne posaient que les
            # métadonnées, d'où les 404 « Fichier non disponible »).
            chemin_abs = os.path.join(
                settings.MEDIA_ROOT, 'plans', str(plan_obj.id_pg), fdata['nom_fichier']
            )
            taille = _write_demo_fichier(chemin_abs, fdata.get('extension'), fdata.get('titre') or fdata['nom_fichier'])
            fdata['taille_fichier'] = taille

            CorPgFichier.objects.update_or_create(
                plan_de_gestion=plan_obj,
                nom_fichier=fdata['nom_fichier'],
                defaults={
                    **fdata,
                    'chemin_fichier': chemin_abs,
                    'id_utilisateur_upload': uploader,
                }
            )
            fichiers_count += 1
            self.log_item('fichier', f'{fdata["nom_fichier"]} → {plan_obj.nom[:40]}...')

        self.log_summary(fichiers_count, 'documents de test')

        # #348 — Bac à sable suppression / duplication (chaîne dédiée, isolée).
        if plan_initial_type and eval_mi_type and plan_revise_type:
            sandbox_plans = self._seed_sandbox(
                admin, sites, (plan_initial_type, eval_mi_type, plan_revise_type)
            )
            plans.extend(sandbox_plans)

        self.log_summary(len(plans), 'plans de gestion')
        self.context.set('plans', plans)
        return plans

    def reset(self) -> int:
        """
        Supprime les plans de gestion de test.

        Returns:
            Nombre de plans supprimés
        """
        CorPgFichier.objects.all().delete()
        return PlanGestion.objects.all().delete()[0]

    def get_dry_run_summary(self) -> List[str]:
        """
        Résumé des plans qui seraient créés.

        Returns:
            Liste des lignes du résumé
        """
        return [
            '\nPlans de gestion principaux (10):',
            '  - Plan 2020-2030 Camargue (valide) - multisites',
            '  - Plan 2018-2028 Aiguilles Rouges (valide) - admin membre',
            '  - Plan 2022-2032 Grand-Voyeux (draft) - CEN',
            '  - Plan inter-sites Vercors-Écrins 2021-2031 (valide) - multisites',
            '  - Plan 2019-2029 Marais de Brouage (archive) - DREAL',
            '  - Plan 2023-2033 Lacs et zones humides (draft) - multisites',
            '  - Plan 2010-2020 Camargue et Brouage ancien (archive) - multisites',
            '  - Plan 2008-2018 Aiguilles Rouges ancien (archive)',
            '  - Plan complémentaire 2024-2034 Littoral (valide) - multisites, sans membres',
            '  - Plan 2025-2035 Lac de Remoray phase 2 (draft) - sans membres',
            '\nChaînes de versions (8 plans historiques):',
            '  Camargue (5 niveaux):',
            '    v1.0 Plan initial 2000-2010 (archive)',
            '    v1.1 → Eval mi-parcours 2005 (archive)',
            '    v2.0 → Plan révisé 2010-2020 (archive)',
            '    v3.0 → Plan actuel 2020-2030 (valide)',
            '    v3.1 → Eval mi-parcours 2025 (draft)',
            '  Aiguilles Rouges (4 niveaux):',
            '    v1.0 Plan initial 2008-2018 (archive)',
            '    v2.0 → Plan révisé 2018-2028 (valide)',
            '    v2.1 → Eval mi-parcours 2023 (valide)',
            '    v2.2 → Plan révisé (draft)',
            '  Vercors-Écrins (3 niveaux):',
            '    v1.0 Plan initial 2011-2021 (archive)',
            '    v2.0 → Plan révisé 2021-2031 (valide)',
            '    v2.1 → Eval mi-parcours 2026 (draft)',
            '\nBac à sable suppression/duplication (#348) — 4 plans :',
            '  Rang 1 : v1 Plan initial 2010-2020 (valide, avec 2 enjeux)',
            '           → v2 Plan révisé 2020-2030 (modifie)',
            '           → v3 Éval mi-parcours 2025 (modifie + is_mi_parcours)',
            '  Rang 2 : brouillon 2030-2040 (draft)',
            '\nDocuments de test (10):',
            '  - Camargue: 3 docs (2 PDF publics + 1 carte)',
            '  - Aiguilles Rouges: 2 docs (1 PdG + 1 annexe)',
            '  - Lacs et zones humides: 3 docs (1 diagnostic + 1 carte + 1 inventaire)',
            '  - Vercors-Écrins: 2 docs (1 rapport + 1 photo)',
        ]
