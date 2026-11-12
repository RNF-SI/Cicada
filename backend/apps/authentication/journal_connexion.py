"""Journal des connexions (``audit.log``) : succès et refus, avec l'adresse.

Sans lui, une série d'essais de mot de passe ou une connexion inattendue d'un
super admin ne laissait aucune trace. La saisie d'un refus n'est pas recopiée
telle quelle (un mot de passe tapé dans le champ identifiant finirait dans les
journaux) : seule son empreinte courte l'est, assez pour regrouper les essais.
"""
import hashlib
import logging

audit_logger = logging.getLogger('audit')


def _empreinte(saisie):
    return hashlib.sha256((saisie or '').strip().lower().encode()).hexdigest()[:12]


def succes(id_role, ip, mode):
    audit_logger.info(
        f'CONNEXION: succès compte={id_role} mode={mode}',
        extra={'action': 'login', 'success': True, 'user_id': id_role, 'ip': ip, 'mode': mode},
    )


def refus(saisie, ip, motif):
    audit_logger.warning(
        f'CONNEXION: refus saisie={_empreinte(saisie)} motif={motif}',
        extra={'action': 'login', 'success': False, 'saisie': _empreinte(saisie), 'ip': ip, 'motif': motif},
    )
