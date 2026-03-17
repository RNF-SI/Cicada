"""
Service de duplication de Plans de Gestion.
"""
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
            ObjectifLongTerme, EtatActuel, NiveauExigence,
            ObjectifOperationnel, ResultatAttendu,
            CorEnjeuTaxon, CorEnjeuHabitat, CorEnjeuGeologie,
        )
        from .models_indicateurs import (
            Indicateur, Metrique,
            CorIndicateurTaxon, CorIndicateurHabitat, CorIndicateurGeologie,
        )

        # If sub_elements requested without enjeux, ignore
        if copy_sub_elements and not copy_enjeux:
            copy_sub_elements = False

        # 1. Generate unique name
        new_name = PlanDuplicationService._generate_unique_name(
            source_plan.nom, PlanGestion
        )

        # 2. Copy plan (linked as new version via plan_parent)
        source_id = source_plan.id_pg
        new_plan = PlanGestion(
            nom=new_name,
            slug='',  # Will be auto-generated in save()
            plan_parent=source_plan,
            id_cdr=source_plan.id_cdr,
            rang=source_plan.rang,
            statut='draft',
            version=source_plan.get_next_version(),
            annee_debut=source_plan.annee_debut,
            annee_fin=source_plan.annee_fin,
            surface=source_plan.surface,
            gestion_partagee=source_plan.gestion_partagee,
            ct88=source_plan.ct88,
            risque_incendie=source_plan.risque_incendie,
            date_validation_cspn=source_plan.date_validation_cspn,
            id_docgestion_fcen=source_plan.id_docgestion_fcen,
            id_evaluation=source_plan.id_evaluation,
            id_redacteur_type=source_plan.id_redacteur_type,
            redacteur_nom=source_plan.redacteur_nom,
            redacteurs=source_plan.redacteurs,
            relecteurs=source_plan.relecteurs,
            commentaire=source_plan.commentaire,
            geometrie=None,
            id_utilisateur_ajout=user,
            id_utilisateur_maj=user,
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

        # 6. Copy enjeux + hierarchy
        if copy_enjeux:
            PlanDuplicationService._copy_enjeux(
                source_id, new_plan, user, copy_sub_elements
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
    def _copy_enjeux(source_plan_id, new_plan, user, copy_sub_elements):
        """Copy enjeux/FCR with their M2M and optionally sub-elements."""
        from .models_enjeux import (
            Enjeu, FacteurInfluence, Pression,
            ObjectifLongTerme, EtatActuel, NiveauExigence,
            ObjectifOperationnel, ResultatAttendu,
            CorEnjeuTaxon, CorEnjeuHabitat, CorEnjeuGeologie,
        )
        from .models_indicateurs import (
            Indicateur, Metrique,
            CorIndicateurTaxon, CorIndicateurHabitat, CorIndicateurGeologie,
        )

        enjeux = Enjeu.objects.filter(id_pg_id=source_plan_id)

        for old_enjeu in enjeux:
            old_enjeu_id = old_enjeu.id_enjeu

            # Copy enjeu
            new_enjeu = Enjeu(
                id_pg=new_plan,
                id_categorie=old_enjeu.id_categorie,
                libelle=old_enjeu.libelle,
                intitule_court=old_enjeu.intitule_court,
                slug='',  # Auto-generated
                description=old_enjeu.description,
                rang=old_enjeu.rang,
                categorie_ecologique=old_enjeu.categorie_ecologique,
                habitat=old_enjeu.habitat,
                espece=old_enjeu.espece,
                processus=old_enjeu.processus,
                etat_enjeu=old_enjeu.etat_enjeu,
                id_categorie_fcr=old_enjeu.id_categorie_fcr,
                id_importance=old_enjeu.id_importance,
                geom=old_enjeu.geom,
                id_utilisateur_ajout=user,
                id_utilisateur_maj=user,
            )
            new_enjeu.save()

            # Copy enjeu M2M tables
            for cor in CorEnjeuTaxon.objects.filter(id_enjeu_id=old_enjeu_id):
                CorEnjeuTaxon.objects.create(
                    id_enjeu=new_enjeu,
                    cd_nom=cor.cd_nom,
                    nom_complet=cor.nom_complet,
                    nom_vern=cor.nom_vern,
                )
            for cor in CorEnjeuHabitat.objects.filter(id_enjeu_id=old_enjeu_id):
                CorEnjeuHabitat.objects.create(
                    id_enjeu=new_enjeu,
                    cd_hab=cor.cd_hab,
                    lb_hab_fr=cor.lb_hab_fr,
                )
            for cor in CorEnjeuGeologie.objects.filter(id_enjeu_id=old_enjeu_id):
                CorEnjeuGeologie.objects.create(
                    id_enjeu=new_enjeu,
                    id_inpg=cor.id_inpg,
                    nom=cor.nom,
                )

            if not copy_sub_elements:
                continue

            # Copy FacteurInfluence -> Pression + OO -> ResultatAttendu -> Indicateur
            for old_fi in FacteurInfluence.objects.filter(id_enjeu_id=old_enjeu_id):
                old_fi_id = old_fi.id_facteur_influence
                new_fi = FacteurInfluence.objects.create(
                    id_enjeu=new_enjeu,
                    libelle=old_fi.libelle,
                    description=old_fi.description,
                    id_utilisateur_ajout=user,
                    id_utilisateur_maj=user,
                )

                for old_pression in Pression.objects.filter(id_facteur_influence_id=old_fi_id):
                    old_pression_id = old_pression.id_pression
                    new_pression = Pression.objects.create(
                        id_facteur_influence=new_fi,
                        id_pressref=old_pression.id_pressref,
                        libelle=old_pression.libelle,
                        description=old_pression.description,
                        id_utilisateur_ajout=user,
                        id_utilisateur_maj=user,
                    )

                    # Copy OO -> ResultatAttendu -> Indicateur -> Metrique (under this pression)
                    for old_oo in ObjectifOperationnel.objects.filter(id_pression_id=old_pression_id):
                        new_oo = ObjectifOperationnel.objects.create(
                            id_pression=new_pression,
                            libelle=old_oo.libelle,
                            description=old_oo.description,
                            id_utilisateur_ajout=user,
                            id_utilisateur_maj=user,
                        )

                        for old_ra in ResultatAttendu.objects.filter(id_oo=old_oo):
                            new_ra = ResultatAttendu.objects.create(
                                id_oo=new_oo,
                                libelle=old_ra.libelle,
                                description=old_ra.description,
                                id_utilisateur_ajout=user,
                                id_utilisateur_maj=user,
                            )

                            for old_ind in Indicateur.objects.filter(id_resultat_attendu=old_ra):
                                new_ind = PlanDuplicationService._copy_indicateur(
                                    old_ind, user, id_ne=None, id_resultat_attendu=new_ra
                                )
                                PlanDuplicationService._copy_indicateur_relations(
                                    old_ind, new_ind, user
                                )

            # Copy EtatActuel -> OLT -> NiveauExigence -> Indicateur -> Metrique
            for old_ea in EtatActuel.objects.filter(id_enjeu_id=old_enjeu_id):
                new_ea = EtatActuel.objects.create(
                    id_enjeu=new_enjeu,
                    libelle=old_ea.libelle,
                    description=old_ea.description,
                    id_utilisateur_ajout=user,
                    id_utilisateur_maj=user,
                )

                for old_olt in ObjectifLongTerme.objects.filter(id_etat_actuel=old_ea):
                    new_olt = ObjectifLongTerme.objects.create(
                        id_etat_actuel=new_ea,
                        libelle=old_olt.libelle,
                        description=old_olt.description,
                        id_utilisateur_ajout=user,
                        id_utilisateur_maj=user,
                    )

                    # NiveauExigence -> Indicateur -> Metrique
                    for old_ne in NiveauExigence.objects.filter(id_olt=old_olt):
                        new_ne = NiveauExigence.objects.create(
                            id_olt=new_olt,
                            libelle=old_ne.libelle,
                            description=old_ne.description,
                            id_utilisateur_ajout=user,
                            id_utilisateur_maj=user,
                        )

                        for old_ind in Indicateur.objects.filter(id_ne=old_ne):
                            new_ind = PlanDuplicationService._copy_indicateur(
                                old_ind, user, id_ne=new_ne, id_resultat_attendu=None
                            )
                            PlanDuplicationService._copy_indicateur_relations(
                                old_ind, new_ind, user
                            )

    @staticmethod
    def _copy_indicateur(old_ind, user, id_ne=None, id_resultat_attendu=None):
        """Copy a single Indicateur with its parent FK."""
        from .models_indicateurs import Indicateur

        return Indicateur.objects.create(
            id_ne=id_ne,
            id_resultat_attendu=id_resultat_attendu,
            nom_indicateur=old_ind.nom_indicateur,
            description=old_ind.description,
            type_indicateur=old_ind.type_indicateur,
            est_standardise=old_ind.est_standardise,
            id_utilisateur_ajout=user,
            id_utilisateur_maj=user,
        )

    @staticmethod
    def _copy_indicateur_relations(old_ind, new_ind, user):
        """Copy M2M and child objects (Metrique) of an Indicateur."""
        from .models_indicateurs import (
            Metrique, CorIndicateurTaxon, CorIndicateurHabitat,
            CorIndicateurGeologie,
        )

        # M2M tables
        for cor in CorIndicateurTaxon.objects.filter(id_indicateur=old_ind):
            CorIndicateurTaxon.objects.create(
                id_indicateur=new_ind,
                cd_nom=cor.cd_nom,
                nom_complet=cor.nom_complet,
                nom_vern=cor.nom_vern,
            )
        for cor in CorIndicateurHabitat.objects.filter(id_indicateur=old_ind):
            CorIndicateurHabitat.objects.create(
                id_indicateur=new_ind,
                cd_hab=cor.cd_hab,
                lb_hab_fr=cor.lb_hab_fr,
            )
        for cor in CorIndicateurGeologie.objects.filter(id_indicateur=old_ind):
            CorIndicateurGeologie.objects.create(
                id_indicateur=new_ind,
                id_inpg=cor.id_inpg,
                nom=cor.nom,
            )

        # Metriques (exclude Mesures - empirical data)
        for old_met in Metrique.objects.filter(id_indicateur=old_ind):
            Metrique.objects.create(
                id_indicateur=new_ind,
                nom_metrique=old_met.nom_metrique,
                description=old_met.description,
                type_metrique=old_met.type_metrique,
                unite=old_met.unite,
                ponderation=old_met.ponderation,
                etat_reference=old_met.etat_reference,
                score_1_inf=old_met.score_1_inf,
                score_1_sup=old_met.score_1_sup,
                score_2_inf=old_met.score_2_inf,
                score_2_sup=old_met.score_2_sup,
                score_3_inf=old_met.score_3_inf,
                score_3_sup=old_met.score_3_sup,
                score_4_inf=old_met.score_4_inf,
                score_4_sup=old_met.score_4_sup,
                score_5_inf=old_met.score_5_inf,
                score_5_sup=old_met.score_5_sup,
                score_1_label=old_met.score_1_label,
                score_2_label=old_met.score_2_label,
                score_3_label=old_met.score_3_label,
                score_4_label=old_met.score_4_label,
                score_5_label=old_met.score_5_label,
                id_utilisateur_ajout=user,
                id_utilisateur_maj=user,
            )
