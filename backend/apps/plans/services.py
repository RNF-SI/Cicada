"""
Service de duplication de Plans de Gestion.
"""
import copy
import logging
import os
import shutil

from django.db import transaction
from django.utils.text import slugify

from apps.core.services import ActivityService

logger = logging.getLogger(__name__)


class PlanDuplicationService:
    """
    Service pour dupliquer un plan de gestion avec ses éléments configurables.

    Usage:
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=plan,
            user=request.user,
            copy_sites=True,
            copy_referents=True,
            copy_fichiers=False,
            copy_enjeux=True,
            copy_sub_elements=True,
        )
    """

    @staticmethod
    @transaction.atomic
    def duplicate_plan(
        source_plan,
        user,
        copy_sites=True,
        copy_referents=True,
        copy_fichiers=False,
        copy_enjeux=True,
        copy_sub_elements=True,
    ):
        """
        Duplique un plan de gestion avec ses relations configurables.

        Args:
            source_plan: PlanGestion source à dupliquer
            user: Utilisateur effectuant la duplication
            copy_sites: Copier les associations site-plan
            copy_referents: Copier les référents
            copy_fichiers: Copier les fichiers (métadonnées + fichiers physiques)
            copy_enjeux: Copier les enjeux/FCR et leurs M2M
            copy_sub_elements: Copier la hiérarchie sous les enjeux
                (facteurs, pressions, OLT, OO, etc.) - nécessite copy_enjeux=True

        Returns:
            PlanGestion: Le nouveau plan créé
        """
        from .models import PlanGestion, CorSitePg, CorPgFichier, CorRolePlan
        from .models_enjeux import (
            Enjeu, FacteurInfluence, Pression,
            ObjectifLongTerme, NiveauExigence,
            ObjectifOperationnel, ResultatAttendu,
            CorEnjeuTaxon, CorEnjeuHabitat, CorEnjeuGeologie,
        )
        from .models_indicateurs import (
            Indicateur, Metrique,
            CorIndicateurGeologie,
        )

        # If sub_elements requested without enjeux, ignore
        if copy_sub_elements and not copy_enjeux:
            copy_sub_elements = False

        # 1. Generate unique name
        new_name = PlanDuplicationService._generate_unique_name(
            source_plan.nom, PlanGestion
        )

        # 2. Copy plan (linked as new version via plan_parent).
        # #377 — copie TOUTES les métadonnées (dont les validations
        # administratives CSRPN), sauf le statut (repart en draft).
        source_id = source_plan.id_pg
        new_plan = PlanDuplicationService.build_version_plan(
            source_plan, user,
            nom=new_name,
            version=source_plan.get_next_version(),
        )
        # Skip automatic activity signal - we'll log manually
        new_plan._skip_activity_signal = True
        new_plan.save()

        # 3. Copy sites
        if copy_sites:
            for cor_site in CorSitePg.objects.filter(
                plan_de_gestion_id=source_id
            ):
                CorSitePg.objects.create(
                    site=cor_site.site,
                    plan_de_gestion=new_plan,
                    rang=cor_site.rang,
                    commentaire=cor_site.commentaire,
                )

        # 4. Copy referents
        if copy_referents:
            referents = list(
                PlanGestion.objects.get(pk=source_id).referents.all()
            )
            new_plan.referents.set(referents)

        # 5. Copy fichiers
        if copy_fichiers:
            PlanDuplicationService._copy_fichiers(
                source_id, new_plan, user
            )

        # 6. Copy enjeux + hierarchy (+ suivis & opérations si sous-éléments).
        # #377 — Une nouvelle version doit copier TOUT le contenu pour pouvoir
        # être éditée sans impacter les anciennes versions.
        if copy_enjeux:
            indicateur_map, metrique_map = PlanDuplicationService._copy_enjeux(
                source_id, new_plan, user, copy_sub_elements
            )
            if copy_sub_elements:
                # Postes d'abord : les lignes RH des opérations pointent
                # dessus et doivent être remappées vers les copies (#560).
                poste_map = PlanDuplicationService._copy_postes(
                    source_id, new_plan, user
                )
                PlanDuplicationService._copy_suivis_and_operations(
                    source_id, new_plan, user, indicateur_map, metrique_map,
                    poste_map,
                )

        # 7. Recalculate geometry
        if copy_sites:
            new_plan.update_geometrie()

        # 8. Auto-grant access: add the duplicating user as member of the new plan
        CorRolePlan.objects.get_or_create(
            id_role=user,
            plan_de_gestion=new_plan,
            defaults={'referent': True, 'commentaire': 'Créateur par duplication'},
        )

        # 9. Log activity manually
        ActivityService.log_plan_activity(
            plan=new_plan,
            action='create',
            actor=user,
            description=f'Plan de gestion "{new_plan.nom}" créé par duplication de "{source_plan.nom}"',
            metadata={
                'source_plan_id': source_id,
                'source_plan_nom': source_plan.nom,
                'duplication': True,
                'options': {
                    'copy_sites': copy_sites,
                    'copy_referents': copy_referents,
                    'copy_fichiers': copy_fichiers,
                    'copy_enjeux': copy_enjeux,
                    'copy_sub_elements': copy_sub_elements,
                }
            },
        )

        return new_plan

    @staticmethod
    def _generate_unique_name(original_name, model_class):
        """
        Generate a unique name for the duplicated plan.
        Pattern: [En cours d'élaboration] name, [En cours d'élaboration 2] name...
        Truncates original name if needed to stay under 255 chars.
        """
        prefix = "[En cours d'élaboration]"
        max_length = 255

        # Strip existing prefix if present (both old [COPIE] and new format)
        clean_name = original_name
        import re
        match = re.match(r'^\[(COPIE|En cours d\'élaboration)(?:\s+\d+)?\]\s*', clean_name)
        if match:
            clean_name = clean_name[match.end():]

        # Truncate name to leave room for prefix
        max_name_len = max_length - len(prefix) - 1  # -1 for space
        if len(clean_name) > max_name_len:
            clean_name = clean_name[:max_name_len]

        candidate = f"{prefix} {clean_name}"
        if not model_class.objects.filter(nom=candidate).exists():
            return candidate

        # Try incrementing
        counter = 2
        while True:
            prefix_n = f"[En cours d'élaboration {counter}]"
            max_name_len = max_length - len(prefix_n) - 1
            truncated = clean_name[:max_name_len] if len(clean_name) > max_name_len else clean_name
            candidate = f"{prefix_n} {truncated}"
            if not model_class.objects.filter(nom=candidate).exists():
                return candidate
            counter += 1
            if counter > 100:
                raise ValueError("Impossible de générer un nom unique après 100 tentatives")

    @staticmethod
    def _copy_fichiers(source_plan_id, new_plan, user):
        """Copy file metadata and physical files."""
        from .models import CorPgFichier

        for fichier in CorPgFichier.objects.filter(
            plan_de_gestion_id=source_plan_id
        ):
            old_path = fichier.chemin_fichier
            new_fichier = CorPgFichier(
                plan_de_gestion=new_plan,
                nom_fichier=fichier.nom_fichier,
                type_fichier=fichier.type_fichier,
                taille_fichier=fichier.taille_fichier,
                extension=fichier.extension,
                titre=fichier.titre,
                description=fichier.description,
                auteur=fichier.auteur,
                date_document=fichier.date_document,
                public=fichier.public,
                ordre_affichage=fichier.ordre_affichage,
                id_utilisateur_upload=user,
            )

            # Copy physical file if it exists
            if old_path and os.path.exists(old_path):
                new_dir = f"/app/media/plans/{new_plan.id_pg}"
                os.makedirs(new_dir, exist_ok=True)
                new_path = os.path.join(new_dir, fichier.nom_fichier)
                shutil.copy2(old_path, new_path)
                new_fichier.chemin_fichier = new_path
            else:
                new_fichier.chemin_fichier = ''

            new_fichier.save()

    @staticmethod
    def copy_content(source_plan, new_plan, user):
        """Copie tout le contenu (enjeux + hiérarchie + suivis + opérations) d'un
        plan source vers un nouveau plan déjà créé (#377).

        Utilisé par les flux de création de version qui n'utilisent pas
        `duplicate_plan` (évaluation mi-parcours, rang suivant). Le nouveau plan
        devient pleinement éditable sans impact sur la version source.
        """
        source_id = getattr(source_plan, 'id_pg', source_plan)
        indicateur_map, metrique_map = PlanDuplicationService._copy_enjeux(
            source_id, new_plan, user, copy_sub_elements=True
        )
        # Les postes sont copiés AVANT les opérations : les lignes RH
        # prévisionnelles pointent dessus et doivent être remappées (#560).
        poste_map = PlanDuplicationService._copy_postes(
            source_id, new_plan, user
        )
        PlanDuplicationService._copy_suivis_and_operations(
            source_id, new_plan, user, indicateur_map, metrique_map, poste_map
        )

    @staticmethod
    def build_version_plan(source_plan, user, **overrides):
        """Construit (NON sauvegardé) un nouveau plan-version à partir d'un plan
        source.

        Copie TOUTES les métadonnées du plan de gestion — y compris les
        validations administratives CSRPN (`date_avis_csrpn`,
        `date_validation_comite`, `date_arrete_pref`, `numero_arrete_pref`,
        `validation_step`) — puis réinitialise les champs de contrôle et de
        cycle de vie. Le statut repart à `draft` (seule la métadonnée exclue).

        Les `overrides` fixent les champs propres au flux appelant (nom,
        version, id_type_document, rang, années…). #377 / copie des métadonnées.
        """
        new_plan = PlanDuplicationService._dup(
            source_plan, user,
            slug='',                 # régénéré à la sauvegarde
            plan_parent=source_plan,
            statut='draft',          # seule métadonnée NON copiée
            geometrie=None,          # recalculée depuis les sites
            # Attributs de cycle de vie (non métadonnées) : repartent à zéro
            is_mi_parcours=False,
            en_revision=False,
            next_rang_plan=None,
            annees_extension=0,
        )
        for key, value in overrides.items():
            setattr(new_plan, key, value)
        return new_plan

    @staticmethod
    def _dup(old, user, **overrides):
        """Clone superficiel d'une instance (copy + pk=None).

        Réinitialise le PK (l'INSERT générera un nouvel id) et les champs
        d'audit utilisateur, puis applique les overrides (FK remappées, etc.).
        Les timestamps auto_now/auto_now_add sont régénérés à la sauvegarde.
        Retourne l'instance NON sauvegardée (le M2M et les enfants sont gérés
        par l'appelant). #377
        """
        new = copy.copy(old)
        new.pk = None
        # `copy.copy` est superficiel : sans cela `new._state` (et les caches de
        # relations) seraient PARTAGÉS avec `old` — muter l'état du clone
        # corromprait alors l'instance source (db=None → M2M cassés). On donne
        # donc au clone son propre état et on purge les caches hérités.
        new._state = copy.copy(old._state)
        new._state.adding = True
        new._state.db = None
        new._prefetched_objects_cache = {}
        if hasattr(new, '_state') and hasattr(new._state, 'fields_cache'):
            new._state.fields_cache = {}
        concrete = {f.name for f in old._meta.concrete_fields}
        if 'id_utilisateur_ajout' in concrete:
            new.id_utilisateur_ajout = user
        if 'id_utilisateur_maj' in concrete:
            new.id_utilisateur_maj = user
        for key, value in overrides.items():
            setattr(new, key, value)
        return new

    @staticmethod
    def _copy_enjeux(source_plan_id, new_plan, user, copy_sub_elements):
        """Copie les enjeux/FCR (+ liens taxon/habitat/géologie) et, si demandé,
        toute la hiérarchie : facteurs → pressions → OO → RA → indicateurs →
        métriques (+ blocs de score #247), et OLT → NE → indicateurs → métriques.

        Copie l'INTÉGRALITÉ des champs de chaque entité (#377). Les données
        empiriques (mesures, saisies annuelles) ne sont volontairement PAS
        copiées : elles appartiennent à la version d'origine.

        Retourne (indicateur_map, metrique_map) : mappings old_id → nouvelle
        instance, utilisés pour relier les opérations copiées.
        """
        from .models_enjeux import (
            Enjeu, FacteurInfluence, Pression,
            ObjectifLongTerme, NiveauExigence,
            ObjectifOperationnel, ResultatAttendu,
            CorEnjeuTaxon, CorEnjeuHabitat, CorEnjeuGeologie,
            CorFacteurEnjeu, CorOoEnjeu,
        )
        from .models_indicateurs import (
            Indicateur, Metrique, MetriqueScoreBlock,
            CorIndicateurGeologie,
        )

        dup = PlanDuplicationService._dup
        indicateur_map = {}
        metrique_map = {}
        # #552 — Facteurs et OO peuvent être partagés entre plusieurs enjeux du
        # plan. Ces maps vivent donc HORS de la boucle enjeu (portée = plan) :
        # l'élément et son sous-arbre ne sont copiés qu'une fois, puis re-liés à
        # chaque nouvel enjeu. Sinon le partage se perdrait à la duplication
        # (N copies indépendantes au lieu d'un élément commun).
        #   - facteur partagé  → M2M `enjeux` (CorFacteurEnjeu)
        #   - OO partagé       → M2M `pressions`, un même OO pouvant être
        #     rattaché aux pressions de DEUX facteurs, donc de deux enjeux.
        facteur_map = {}
        oo_map = {}
        # #552 — ancien enjeu → nouvel enjeu, pour recopier l'ordre des OO
        # propre à chaque enjeu (CorOoEnjeu) une fois tous les OO créés.
        enjeu_map = {}

        def _copy_indicateur(old_ind, **parent_override):
            new_ind = dup(old_ind, user, **parent_override)
            new_ind.save()
            indicateur_map[old_ind.id_indicateur] = new_ind

            for cor in CorIndicateurGeologie.objects.filter(id_indicateur=old_ind):
                CorIndicateurGeologie.objects.create(
                    id_indicateur=new_ind, id_inpg=cor.id_inpg, nom=cor.nom,
                )

            # Métriques + blocs de score complémentaires (#247)
            for old_met in Metrique.objects.filter(id_indicateur=old_ind):
                new_met = dup(old_met, user, id_indicateur=new_ind)
                new_met.save()
                metrique_map[old_met.id_metrique] = new_met
                for blk in MetriqueScoreBlock.objects.filter(id_metrique=old_met):
                    new_blk = dup(blk, user, id_metrique=new_met)
                    new_blk.save()
            return new_ind

        for old_enjeu in Enjeu.objects.filter(id_pg_id=source_plan_id):
            new_enjeu = dup(old_enjeu, user, id_pg=new_plan, slug='')
            new_enjeu.save()
            enjeu_map[old_enjeu.pk] = new_enjeu

            for cor in CorEnjeuTaxon.objects.filter(id_enjeu=old_enjeu):
                CorEnjeuTaxon.objects.create(
                    id_enjeu=new_enjeu, cd_nom=cor.cd_nom,
                    nom_complet=cor.nom_complet, nom_vern=cor.nom_vern,
                )
            for cor in CorEnjeuHabitat.objects.filter(id_enjeu=old_enjeu):
                CorEnjeuHabitat.objects.create(
                    id_enjeu=new_enjeu, cd_hab=cor.cd_hab, lb_hab_fr=cor.lb_hab_fr,
                )
            for cor in CorEnjeuGeologie.objects.filter(id_enjeu=old_enjeu):
                CorEnjeuGeologie.objects.create(
                    id_enjeu=new_enjeu, id_inpg=cor.id_inpg, nom=cor.nom,
                )

            if not copy_sub_elements:
                continue

            # Facteurs (partagés, #552) → Pressions → OO (M2M, dédupliqués)
            # → RA → Indicateurs
            for old_cor in CorFacteurEnjeu.objects.filter(id_enjeu=old_enjeu):
                old_fi = old_cor.id_facteur_influence

                # Facteur déjà copié via un autre enjeu : on le re-lie au nouvel
                # enjeu sans recopier son sous-arbre (il est partagé, #552).
                if old_fi.pk in facteur_map:
                    CorFacteurEnjeu.objects.create(
                        id_facteur_influence=facteur_map[old_fi.pk],
                        id_enjeu=new_enjeu,
                        ordre=old_cor.ordre,
                    )
                    continue

                new_fi = dup(old_fi, user)
                new_fi.save()
                facteur_map[old_fi.pk] = new_fi
                # L'ordre est porté par la liaison, propre à chaque enjeu (#552).
                CorFacteurEnjeu.objects.create(
                    id_facteur_influence=new_fi,
                    id_enjeu=new_enjeu,
                    ordre=old_cor.ordre,
                )
                for old_pr in Pression.objects.filter(id_facteur_influence=old_fi):
                    new_pr = dup(old_pr, user, id_facteur_influence=new_fi)
                    new_pr.save()
                    for old_oo in old_pr.objectifs_operationnels.all():
                        if old_oo.id_oo not in oo_map:
                            new_oo = dup(old_oo, user)
                            new_oo.save()
                            oo_map[old_oo.id_oo] = new_oo
                            for old_ra in ResultatAttendu.objects.filter(id_oo=old_oo):
                                new_ra = dup(old_ra, user, id_oo=new_oo)
                                new_ra.save()
                                for old_ind in Indicateur.objects.filter(id_resultat_attendu=old_ra):
                                    _copy_indicateur(
                                        old_ind, id_ne=None, id_resultat_attendu=new_ra
                                    )
                        oo_map[old_oo.id_oo].pressions.add(new_pr)

            # OLT → Niveaux d'exigence → Indicateurs
            for old_olt in ObjectifLongTerme.objects.filter(id_enjeu=old_enjeu):
                new_olt = dup(old_olt, user, id_enjeu=new_enjeu)
                new_olt.save()
                for old_ne in NiveauExigence.objects.filter(id_olt=old_olt):
                    new_ne = dup(old_ne, user, id_olt=new_olt)
                    new_ne.save()
                    for old_ind in Indicateur.objects.filter(id_ne=old_ne):
                        _copy_indicateur(old_ind, id_ne=new_ne, id_resultat_attendu=None)

        # #552 — Ordre des OO propre à chaque enjeu (CorOoEnjeu). Recopié en
        # dernier, une fois OO et enjeux créés, via les deux maps. Sans ça, une
        # nouvelle version perdrait l'ordonnancement par enjeu des OO partagés
        # (retour à l'ordre global).
        if copy_sub_elements and oo_map and enjeu_map:
            for cor in CorOoEnjeu.objects.filter(id_enjeu_id__in=enjeu_map.keys()):
                new_oo = oo_map.get(cor.id_oo_id)
                new_enjeu = enjeu_map.get(cor.id_enjeu_id)
                if new_oo is not None and new_enjeu is not None:
                    CorOoEnjeu.objects.create(
                        id_oo=new_oo, id_enjeu=new_enjeu, ordre=cor.ordre,
                    )

        return indicateur_map, metrique_map

    @staticmethod
    def _copy_postes(source_plan_id, new_plan, user):
        """Copie les postes du PG et leurs fonctions (#560).

        Les postes sont rattachés à un plan : une nouvelle version doit avoir
        les siens, éditables sans impacter la version source. L'organisme du
        poste est repris tel quel (entité indépendante du plan).

        Les fonctions du **socle** sont partagées : on les réutilise. Celles
        **propres au plan source** (#631) sont recréées à l'identique pour le
        nouveau plan, sinon la nouvelle version pointerait sur une fonction
        qu'elle n'a pas le droit de voir.

        Retourne {ancien id_poste: nouveau Poste} pour remapper les lignes RH
        des opérations.
        """
        from .models_operations import Fonction, Poste, PosteFonction

        dup = PlanDuplicationService._dup
        fonction_map = {}

        def fonction_pour_le_nouveau_plan(fonction):
            """Socle → telle quelle ; fonction du plan source → sa copie."""
            if fonction is None or fonction.id_pg_id != source_plan_id:
                return fonction
            if fonction.id_fonction not in fonction_map:
                copie, _ = Fonction.objects.get_or_create(
                    libelle=fonction.libelle,
                    id_pg=new_plan,
                    defaults={
                        'type_poste': fonction.type_poste,
                        'finance_par_defaut': fonction.finance_par_defaut,
                        'actif': fonction.actif,
                        'is_socle': False,
                    },
                )
                fonction_map[fonction.id_fonction] = copie
            return fonction_map[fonction.id_fonction]

        poste_map = {}
        for old_poste in Poste.objects.filter(id_pg_id=source_plan_id):
            new_poste = dup(old_poste, user, id_pg=new_plan)
            new_poste.save()
            poste_map[old_poste.id_poste] = new_poste
            for old_fonction in PosteFonction.objects.filter(id_poste=old_poste):
                new_fonction = dup(
                    old_fonction, user, id_poste=new_poste,
                    id_fonction=fonction_pour_le_nouveau_plan(old_fonction.id_fonction),
                )
                new_fonction.save()
        return poste_map

    @staticmethod
    def _copy_suivis_and_operations(source_plan_id, new_plan, user,
                                    indicateur_map, metrique_map,
                                    poste_map=None):
        """Copie les suivis/inventaires du plan puis les opérations (actions),
        en re-reliant chaque opération aux nouvelles entités copiées (#377).

        Une opération est rattachée au plan via son indicateur, ses métriques
        (M2M) ou son suivi. On la clone avec ses années (+ organismes, + lignes
        RH prévisionnelles #560) et ses financements. Les données « réalisées »
        (RealisationOperationAnnee et ses lignes RH) ne sont pas copiées :
        elles concernent la version d'origine.
        """
        from .models_operations import (
            SuiviInventaire, Operation, OperationAnnee,
            OperationAnneeOrganisme, OperationAnneeRH, FinanceOperation,
            CorOperationSite, CorOperationMetrique,
        )

        poste_map = poste_map or {}

        dup = PlanDuplicationService._dup

        # 1. Suivis / inventaires (rattachés directement au plan).
        suivi_map = {}
        for old_suivi in SuiviInventaire.objects.filter(
            id_pg_id=source_plan_id
        ).prefetch_related('protocoles'):
            new_suivi = dup(old_suivi, user, id_pg=new_plan)
            new_suivi.save()
            # Les protocoles sont clonés et non partagés : sans cela le plan copié
            # pointerait les mêmes lignes que la source, et les éditer depuis la
            # nouvelle version modifierait aussi l'ancienne (#252).
            for old_proto in old_suivi.protocoles.all():
                new_proto = dup(old_proto, user)
                new_proto.save()
                new_suivi.protocoles.add(new_proto)
            suivi_map[old_suivi.id_suivi_inventaire] = new_suivi

        # 2. Identifier les opérations du plan (indicateur, métriques ou suivi).
        op_ids = set()
        if indicateur_map:
            op_ids |= set(
                Operation.objects.filter(id_indicateur_id__in=indicateur_map.keys())
                .values_list('id_operation', flat=True)
            )
            op_ids |= set(
                Operation.objects.filter(metriques__id_metrique__in=metrique_map.keys())
                .values_list('id_operation', flat=True)
            )
        if suivi_map:
            op_ids |= set(
                Operation.objects.filter(id_suivi_id__in=suivi_map.keys())
                .values_list('id_operation', flat=True)
            )

        for old_op in Operation.objects.filter(id_operation__in=op_ids):
            overrides = {}
            if old_op.id_indicateur_id:
                overrides['id_indicateur'] = indicateur_map.get(old_op.id_indicateur_id)
            if old_op.id_suivi_id:
                overrides['id_suivi'] = suivi_map.get(old_op.id_suivi_id)
            new_op = dup(old_op, user, **overrides)
            new_op.save()

            # M2M métriques (via through) — remappées vers les nouvelles métriques.
            for old_met in old_op.metriques.all():
                new_met = metrique_map.get(old_met.id_metrique)
                if new_met is not None:
                    CorOperationMetrique.objects.create(
                        id_operation=new_op, id_metrique=new_met
                    )
            # M2M sites (via through) — mêmes sites (entités indépendantes du plan).
            for site in old_op.sites.all():
                CorOperationSite.objects.create(id_operation=new_op, id_site=site)

            # Années de programmation (+ ventilation par organisme).
            for old_oa in OperationAnnee.objects.filter(id_operation=old_op):
                new_oa = dup(old_oa, user, id_operation=new_op)
                new_oa.save()
                for old_org in OperationAnneeOrganisme.objects.filter(id_operation_annee=old_oa):
                    new_org = dup(old_org, user, id_operation_annee=new_oa)
                    new_org.save()
                # Lignes RH prévisionnelles (#560) : le poste est remappé vers
                # la copie du plan ; l'organisme, entité indépendante du plan,
                # reste partagé. Un poste absent de la map (donnée incohérente)
                # dégrade en « temps non affecté » plutôt que de pointer vers
                # la version source.
                for old_rh in OperationAnneeRH.objects.filter(id_operation_annee=old_oa):
                    new_rh = dup(
                        old_rh, user,
                        id_operation_annee=new_oa,
                        id_poste=poste_map.get(old_rh.id_poste_id),
                    )
                    new_rh.save()

            # Financements.
            for old_fin in FinanceOperation.objects.filter(id_operation=old_op):
                new_fin = dup(old_fin, user, id_operation=new_op)
                new_fin.save()
