"""
Copie profonde d'un élément unique de l'arborescence d'un plan (#552).

Alternative au **lien** (#552) : plutôt que de partager un facteur / OO / action
entre plusieurs enjeux (entité unique répétée), on peut le **copier** — un
duplicata indépendant, modifiable sans impacter l'original.

Contrairement à ``PlanDuplicationService`` (qui clone tout un plan), on ne copie
ici qu'**une branche** et on la rattache à une cible du **même plan** :

- un **facteur** → copié avec ses pressions → OO → RA → indicateurs → métriques
  → actions, rattaché à un enjeu cible ;
- un **OO** → copié avec ses RA → indicateurs → …, rattaché à une pression
  (cas Enjeu) ou directement à un enjeu (cas FCR) ;
- une **action** → copiée avec sa programmation (années, organismes, RH, sites,
  financements), rattachée à une métrique ou un indicateur cible.

On réutilise ``PlanDuplicationService._dup`` (clone superficiel + reset audit) et
le même parti pris que la duplication de plan : les **entités indépendantes du
plan** (sites, organismes, postes, suivis) sont **conservées par référence**, et
les **données empiriques** (réalisations) ne sont **pas** copiées.
"""
from django.db import transaction

from .services import PlanDuplicationService


class ElementCopyService:
    """Copie profonde d'un facteur / OO / action vers une cible du même plan."""

    # ------------------------------------------------------------------ actions
    @staticmethod
    def _copy_operation(old_op, user, *, id_indicateur=None, metrique_links=()):
        """Clone une action + sa programmation, sans les réalisations (#377).

        - ``id_indicateur`` : nouvel indicateur de rattachement direct (#367),
          ou None si l'action n'est rattachée que par ses métriques.
        - ``metrique_links`` : métriques (nouvelles) à relier en M2M.
        Le suivi (``id_suivi``), les sites et les postes sont conservés tels
        quels : ce sont des ressources du plan, pas de la branche copiée.
        """
        from .models_operations import (
            Operation, OperationAnnee, OperationAnneeOrganisme,
            OperationAnneeRH, FinanceOperation, CorOperationSite,
            CorOperationMetrique,
        )

        dup = PlanDuplicationService._dup
        new_op = dup(old_op, user, id_indicateur=id_indicateur)
        new_op.save()

        for new_met in metrique_links:
            CorOperationMetrique.objects.create(id_operation=new_op, id_metrique=new_met)
        for site in old_op.sites.all():
            CorOperationSite.objects.create(id_operation=new_op, id_site=site)

        for old_oa in OperationAnnee.objects.filter(id_operation=old_op):
            new_oa = dup(old_oa, user, id_operation=new_op)
            new_oa.save()
            for old_org in OperationAnneeOrganisme.objects.filter(id_operation_annee=old_oa):
                dup(old_org, user, id_operation_annee=new_oa).save()
            # Lignes RH prévisionnelles (#560) : même plan → mêmes postes.
            for old_rh in OperationAnneeRH.objects.filter(id_operation_annee=old_oa):
                dup(old_rh, user, id_operation_annee=new_oa).save()

        for old_fin in FinanceOperation.objects.filter(id_operation=old_op):
            dup(old_fin, user, id_operation=new_op).save()

        return new_op

    # -------------------------------------------------------------- indicateurs
    @staticmethod
    def _copy_indicateur(old_ind, user, **parent_override):
        """Clone un indicateur + cor géol + métriques (+ blocs)
        + les actions rattachées (directement ou via ses métriques)."""
        from .models_indicateurs import (
            Indicateur, Metrique, MetriqueScoreBlock,
            CorIndicateurGeologie,
        )
        from .models_operations import Operation

        dup = PlanDuplicationService._dup
        new_ind = dup(old_ind, user, **parent_override)
        new_ind.save()

        for cor in CorIndicateurGeologie.objects.filter(id_indicateur=old_ind):
            CorIndicateurGeologie.objects.create(
                id_indicateur=new_ind, id_inpg=cor.id_inpg, nom=cor.nom,
            )

        metrique_map = {}
        for old_met in Metrique.objects.filter(id_indicateur=old_ind):
            new_met = dup(old_met, user, id_indicateur=new_ind)
            new_met.save()
            metrique_map[old_met.id_metrique] = new_met
            for blk in MetriqueScoreBlock.objects.filter(id_metrique=old_met):
                dup(blk, user, id_metrique=new_met).save()

        # Actions rattachées à cet indicateur : directement (#367) ou via une
        # de ses métriques. Dédupliquées (une action liée à 2 métriques du même
        # indicateur ne doit être copiée qu'une fois).
        op_ids = set(
            Operation.objects.filter(id_indicateur=old_ind)
            .values_list('id_operation', flat=True)
        )
        op_ids |= set(
            Operation.objects.filter(metriques__id_metrique__in=metrique_map.keys())
            .values_list('id_operation', flat=True)
        )
        for old_op in Operation.objects.filter(id_operation__in=op_ids):
            id_ind = new_ind if old_op.id_indicateur_id == old_ind.pk else None
            links = [
                metrique_map[m.id_metrique]
                for m in old_op.metriques.all()
                if m.id_metrique in metrique_map
            ]
            ElementCopyService._copy_operation(
                old_op, user, id_indicateur=id_ind, metrique_links=links,
            )
        return new_ind

    # ------------------------------------------------------------------- OO core
    @staticmethod
    def _copy_oo_core(old_oo, user):
        """Clone un OO + ses RA + leurs indicateurs (sans rattachement : le
        caller pose le lien pression/enjeu). Retourne le nouvel OO."""
        from .models_enjeux import ResultatAttendu
        from .models_indicateurs import Indicateur

        dup = PlanDuplicationService._dup
        # Rattachement posé par le caller → on repart sans enjeu direct.
        new_oo = dup(old_oo, user, id_enjeu=None)
        new_oo.save()

        # #585 — tout ce qui s'AFFICHE sous l'OO est copié, y compris un
        # résultat attendu qui y est seulement partagé (porté par un autre
        # objectif) : la copie doit ressembler à ce qu'on voit à l'écran.
        for old_ra in ResultatAttendu.objects.filter(objectifs_operationnels=old_oo).distinct():
            new_ra = dup(old_ra, user, id_oo=new_oo)
            new_ra.save()
            for old_ind in Indicateur.objects.filter(id_resultat_attendu=old_ra):
                ElementCopyService._copy_indicateur(
                    old_ind, user, id_ne=None, id_resultat_attendu=new_ra,
                )
        return new_oo

    # ---------------------------------------------------------------- public API
    @staticmethod
    @transaction.atomic
    def copy_facteur(old_facteur, user, *, target_enjeu):
        """Copie un facteur + tout son sous-arbre, rattaché à ``target_enjeu``."""
        from .models_enjeux import Pression, CorFacteurEnjeu
        from django.db.models import Max

        dup = PlanDuplicationService._dup
        new_fi = dup(old_facteur, user)
        new_fi.save()

        max_ordre = CorFacteurEnjeu.objects.filter(
            id_enjeu=target_enjeu
        ).aggregate(m=Max('ordre'))['m']
        CorFacteurEnjeu.objects.create(
            id_facteur_influence=new_fi, id_enjeu=target_enjeu,
            ordre=(max_ordre + 1) if max_ordre is not None else 0,
        )

        # Un OO partagé entre 2 pressions du MÊME facteur n'est copié qu'une fois.
        oo_map = {}
        for old_pr in Pression.objects.filter(id_facteur_influence=old_facteur):
            new_pr = dup(old_pr, user, id_facteur_influence=new_fi)
            new_pr.save()
            for old_oo in old_pr.objectifs_operationnels.all():
                new_oo = oo_map.get(old_oo.id_oo)
                if new_oo is None:
                    new_oo = ElementCopyService._copy_oo_core(old_oo, user)
                    oo_map[old_oo.id_oo] = new_oo
                new_oo.pressions.add(new_pr)
        return new_fi

    @staticmethod
    @transaction.atomic
    def copy_oo(old_oo, user, *, target_pression=None, target_enjeu=None):
        """Copie un OO + son sous-arbre, rattaché à une pression (cas Enjeu) ou
        directement à un enjeu (cas FCR). Exactement une cible attendue."""
        if (target_pression is None) == (target_enjeu is None):
            raise ValueError("Fournir soit target_pression, soit target_enjeu (exclusif).")

        new_oo = ElementCopyService._copy_oo_core(old_oo, user)
        if target_pression is not None:
            new_oo.pressions.add(target_pression)
        else:
            new_oo.id_enjeu = target_enjeu
            new_oo.save(update_fields=['id_enjeu'])
        return new_oo

    @staticmethod
    @transaction.atomic
    def copy_ra(old_ra, user, *, target_oo):
        """
        Copie un résultat attendu + ses indicateurs sous ``target_oo`` (#585).

        Contrairement à ``link`` (entité unique partagée), produit un duplicata
        INDÉPENDANT : le modifier n'a aucun effet sur l'original.
        """
        from .models_indicateurs import Indicateur

        dup = PlanDuplicationService._dup
        new_ra = dup(old_ra, user, id_oo=target_oo)
        new_ra.save()   # pose aussi le lien de liaison porteur (invariant #585)

        for old_ind in Indicateur.objects.filter(id_resultat_attendu=old_ra):
            ElementCopyService._copy_indicateur(
                old_ind, user, id_ne=None, id_resultat_attendu=new_ra,
            )
        return new_ra

    @staticmethod
    @transaction.atomic
    def copy_operation(old_op, user, *, target_metrique=None, target_indicateur=None):
        """Copie une action + sa programmation, rattachée à une métrique ou un
        indicateur cible (existants). Exactement une cible attendue."""
        if (target_metrique is None) == (target_indicateur is None):
            raise ValueError("Fournir soit target_metrique, soit target_indicateur (exclusif).")

        return ElementCopyService._copy_operation(
            old_op, user,
            id_indicateur=target_indicateur,
            metrique_links=[target_metrique] if target_metrique is not None else (),
        )
