"""
#423 — Tests unitaires du calcul du score d'une métrique à partir d'une valeur.

Couvre les deux symptômes corrigés :
  1. Les paliers extrêmes à borne ouverte (très mauvais ouvert vers le bas,
     très bon ouvert vers le haut) ne doivent plus être ignorés.
  2. La virgule décimale française (« 20,6 ») ne doit plus être tronquée.

Les fonctions testées sont pures (lecture des seuils via getattr) : on utilise
un stub de métrique, sans base de données.
"""
import pytest

# Charger d'abord serializers_enjeux pour éviter un import circulaire au
# chargement isolé de views_indicateurs (ordre d'import only).
import apps.plans.serializers_enjeux  # noqa: F401
from apps.plans.views_indicateurs import _value_to_score, _coerce_float


class _MetriqueStub:
    """Grille de scores type (cf. capture #423) :
    très mauvais ]−∞ ; 5], mauvais ]5 ; 10], moyen, bon, très bon ]20 ; +∞[."""
    inactive_levels = []
    score_1_inf = None
    score_1_sup = 5
    score_2_inf = 5
    score_2_sup = 10
    score_3_inf = 10
    score_3_sup = 15
    score_4_inf = 15
    score_4_sup = 20
    score_5_inf = 20
    score_5_sup = None


@pytest.fixture
def met():
    return _MetriqueStub()


class TestCoerceFloat:
    def test_virgule_francaise(self):
        assert _coerce_float('20,6') == 20.6

    def test_point_decimal(self):
        assert _coerce_float('20.6') == 20.6

    def test_nombre(self):
        assert _coerce_float(12) == 12.0

    def test_espaces(self):
        assert _coerce_float('  3,5 ') == 3.5

    @pytest.mark.parametrize('bad', [None, '', 'abc', 'NaN-x'])
    def test_invalide(self, bad):
        assert _coerce_float(bad) is None


class TestValueToScore:
    def test_borne_basse_ouverte_palier_extreme(self, met):
        """#423 — value=5 doit tomber dans « très mauvais » (palier ouvert vers
        le bas), pas être ignoré. C'était le bug principal."""
        assert _value_to_score(5, met) == 1
        assert _value_to_score(3, met) == 1
        assert _value_to_score(-100, met) == 1

    def test_borne_haute_ouverte_palier_extreme(self, met):
        """#423 — value au-dessus de 20 doit tomber dans « très bon »."""
        assert _value_to_score(25, met) == 5
        assert _value_to_score(20.6, met) == 5

    def test_virgule_decimale_non_tronquee(self, met):
        """#423 — « 20,6 » ne doit pas devenir 20 (qui resterait en « bon »)."""
        assert _value_to_score('20,6', met) == 5
        # contraste : 20 pile est dans « bon » (15..20)
        assert _value_to_score('20', met) == 4

    def test_paliers_intermediaires(self, met):
        assert _value_to_score(7, met) == 2
        assert _value_to_score(12, met) == 3
        assert _value_to_score(17, met) == 4

    def test_valeur_non_numerique(self, met):
        assert _value_to_score('xyz', met) is None
        assert _value_to_score(None, met) is None

    def test_palier_desactive_est_saute(self, met):
        met.inactive_levels = [1]
        # value=3 tomberait en palier 1, mais 1 est désactivé → aucun palier
        assert _value_to_score(3, met) is None
        met.inactive_levels = []

    def test_inclusivite_bornes_partagees(self):
        """#423 (suite) — grille DÉCROISSANTE type phosphore :
        ≥50 / ]35;50] / ]20;35] / ]10;20] / ]0;10]. La valeur 35 doit tomber dans
        le palier dont la borne SUP vaut 35 (35 inclus = Moyen), pas dans celui
        dont la borne INF vaut 35 (35 exclu = Mauvais)."""
        class M:
            inactive_levels = []
            score_1_inf = 50; score_1_sup = None
            score_2_inf = 35; score_2_sup = 50
            score_3_inf = 20; score_3_sup = 35
            score_4_inf = 10; score_4_sup = 20
            score_5_inf = 0;  score_5_sup = 10
            # toutes les bornes sup inclusives (défaut)
            score_1_sup_inclusive = True
            score_2_sup_inclusive = True
            score_3_sup_inclusive = True
            score_4_sup_inclusive = True
        m = M()
        assert _value_to_score(35, m) == 3   # Moyen (35 inclus dans ]20;35])
        assert _value_to_score(50, m) == 1   # ≥50 (palier extrême gagne)
        assert _value_to_score(36, m) == 2   # Mauvais ]35;50]
        assert _value_to_score(20, m) == 4   # Bon (20 inclus dans ]10;20])
        assert _value_to_score(10, m) == 5   # Très bon (10 inclus dans ]0;10])
        assert _value_to_score(5, m) == 5    # Très bon

    def test_les_deux_bornes_nulles_palier_ignore(self):
        class M:
            inactive_levels = []
            # palier 1 totalement vide → ignoré
            score_1_inf = None
            score_1_sup = None
            score_2_inf = 0
            score_2_sup = 10
            score_3_inf = score_3_sup = None
            score_4_inf = score_4_sup = None
            score_5_inf = score_5_sup = None
        assert _value_to_score(5, M()) == 2


class TestValueToScoreDoublons:
    """#453 — un même libellé/chiffre défini sur ≥2 niveaux rend la valeur
    ambiguë : le score ne peut pas être auto-calculé (→ None, saisie manuelle).
    Une valeur qui tombe sur un palier unique reste, elle, résolue."""

    def test_texte_libelle_duplique_est_indetermine(self):
        class M:
            inactive_levels = []
            score_1_label = 'Absent'
            score_2_label = 'Présent'
            score_3_label = 'Moyen'
            score_4_label = 'Présent'   # doublon du niveau 2
            score_5_label = 'Abondant'
        assert _value_to_score('Présent', M()) is None   # ambigu (2 et 4)
        assert _value_to_score('Absent', M()) == 1        # unique
        assert _value_to_score('Moyen', M()) == 3         # unique

    def test_chiffre_valeur_dupliquee_est_indetermine(self):
        class M:
            inactive_levels = []
            score_1_val = 0
            score_2_val = 10
            score_3_val = 20
            score_4_val = 10   # doublon du niveau 2
            score_5_val = 40
        assert _value_to_score(10, M()) is None   # ambigu (2 et 4)
        assert _value_to_score('10', M()) is None
        assert _value_to_score(0, M()) == 1       # unique
        assert _value_to_score(20, M()) == 3      # unique

    def test_doublon_leve_si_un_niveau_desactive(self):
        class M:
            inactive_levels = [4]   # le doublon niveau 4 est désactivé
            score_1_label = 'Absent'
            score_2_label = 'Présent'
            score_3_label = 'Moyen'
            score_4_label = 'Présent'
            score_5_label = 'Abondant'
        assert _value_to_score('Présent', M()) == 2   # plus qu'une correspondance active


# =============================================================================
# #247 — Score combiné multi-blocs (formule ET/OU + parenthèses)
# =============================================================================
from apps.plans.views_indicateurs import combine_block_scores, _mesure_to_score


class TestCombineBlockScores:
    """Évaluateur pur : OU=max, ET=min, ET>OU, parenthèses, None neutre."""

    def test_ou_prend_le_max(self):
        assert combine_block_scores([('val', 4), ('op', 'OR'), ('val', 2)]) == 4

    def test_et_prend_le_min(self):
        assert combine_block_scores([('val', 4), ('op', 'AND'), ('val', 2)]) == 2

    def test_parentheses(self):
        # (A OU B) ET C : (max(4,2)=4) ET 3 = 3
        assert combine_block_scores([
            ('lparen',), ('val', 4), ('op', 'OR'), ('val', 2), ('rparen',),
            ('op', 'AND'), ('val', 3),
        ]) == 3

    def test_precedence_et_avant_ou(self):
        # A OU B ET C = A OU (B ET C) : 1 OU (min(5,3)=3) = 3
        assert combine_block_scores([
            ('val', 1), ('op', 'OR'), ('val', 5), ('op', 'AND'), ('val', 3),
        ]) == 3
        # A ET B OU C = (A ET B) OU C : (min(5,2)=2) OU 3 = 3
        assert combine_block_scores([
            ('val', 5), ('op', 'AND'), ('val', 2), ('op', 'OR'), ('val', 3),
        ]) == 3

    def test_none_neutre(self):
        assert combine_block_scores([('val', 4), ('op', 'AND'), ('val', None)]) == 4
        assert combine_block_scores([('val', None), ('op', 'OR'), ('val', 3)]) == 3
        assert combine_block_scores([('val', None), ('op', 'OR'), ('val', None)]) is None

    def test_cas_degeneres(self):
        assert combine_block_scores([]) is None
        assert combine_block_scores([('val', 3)]) == 3


class _Blk:
    """Stub de MetriqueScoreBlock (mêmes attributs de scoring qu'une métrique)."""
    def __init__(self, position, logical_op, bounds, group_open=0, group_close=0):
        self.position = position
        self.logical_op = logical_op
        self.group_open = group_open
        self.group_close = group_close
        self.inactive_levels = []
        for i in range(1, 6):
            inf, sup = bounds.get(i, (None, None))
            setattr(self, f'score_{i}_inf', inf)
            setattr(self, f'score_{i}_sup', sup)
        for i in range(1, 5):
            setattr(self, f'score_{i}_sup_inclusive', True)


class _Mgr:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)


class _MetMulti:
    """Métrique NUMERIQUE croissante 0-2/2-4/4-6/6-8/8-10 + blocs complémentaires."""
    inactive_levels = []
    group_open = 0
    group_close = 0
    score_1_inf, score_1_sup = 0, 2
    score_2_inf, score_2_sup = 2, 4
    score_3_inf, score_3_sup = 4, 6
    score_4_inf, score_4_sup = 6, 8
    score_5_inf, score_5_sup = 8, 10

    def __init__(self, blocks):
        self.score_blocks = _Mgr(blocks)


class _Mesure:
    def __init__(self, valeur, valeurs_blocs=None):
        self.valeur = valeur
        self.valeurs_blocs = valeurs_blocs or {}


class TestMesureToScore:
    def test_mono_bloc_delegue_a_value_to_score(self):
        met = _MetMulti([])
        assert _mesure_to_score(_Mesure('5'), met) == 3   # 5 ∈ ]4;6]
        assert _mesure_to_score(None, met) is None

    def test_multi_bloc_ou(self):
        # Principal OU Bloc1 (mêmes seuils). val principal=5 (score3), bloc=9 (score5) → max=5
        blk = _Blk(1, 'OR', {1: (0, 2), 2: (2, 4), 3: (4, 6), 4: (6, 8), 5: (8, 10)})
        met = _MetMulti([blk])
        mes = _Mesure('5', {'1': '9'})
        assert _mesure_to_score(mes, met) == 5

    def test_multi_bloc_et(self):
        # Principal ET Bloc1 : val=5 (3), bloc=9 (5) → min=3
        blk = _Blk(1, 'AND', {1: (0, 2), 2: (2, 4), 3: (4, 6), 4: (6, 8), 5: (8, 10)})
        met = _MetMulti([blk])
        assert _mesure_to_score(_Mesure('5', {'1': '9'}), met) == 3

    def test_multi_bloc_parenthese(self):
        # (Principal OU Bloc1) ET Bloc2 : val=1(1), b1=9(5), b2=5(3) → (max(1,5)=5) ET 3 = 3
        b1 = _Blk(1, 'OR', {1: (0, 2), 2: (2, 4), 3: (4, 6), 4: (6, 8), 5: (8, 10)}, group_close=1)
        b2 = _Blk(2, 'AND', {1: (0, 2), 2: (2, 4), 3: (4, 6), 4: (6, 8), 5: (8, 10)})
        met = _MetMulti([b1, b2])
        met.group_open = 1
        assert _mesure_to_score(_Mesure('1', {'1': '9', '2': '5'}), met) == 3

    def test_bloc_sans_valeur_ignore(self):
        # val principal=5 (3), bloc sans valeur (None neutre) → 3
        blk = _Blk(1, 'AND', {1: (0, 2), 2: (2, 4), 3: (4, 6), 4: (6, 8), 5: (8, 10)})
        met = _MetMulti([blk])
        assert _mesure_to_score(_Mesure('5', {}), met) == 3


# =============================================================================
# #452 — _value_to_score type-aware (TEXTE / CHIFFRE), miroir du frontend
# =============================================================================
class _TypeMet:
    """Stub avec type_metrique.mnemonique explicite."""
    inactive_levels = []

    class _T:
        def __init__(self, m):
            self.mnemonique = m

    def __init__(self, mnem, **scores):
        self.type_metrique = self._T(mnem)
        for i in range(1, 6):
            setattr(self, f'score_{i}_label', scores.get(f'l{i}'))
            setattr(self, f'score_{i}_val', scores.get(f'v{i}'))
            setattr(self, f'score_{i}_inf', scores.get(f'inf{i}'))
            setattr(self, f'score_{i}_sup', scores.get(f'sup{i}'))


class TestValueToScoreTexte:
    def test_libelle_correspondant(self):
        m = _TypeMet('TEXTE', l1='Mauvais', l2='Moyen', l3='Bon', l4='Très bon', l5='Optimal')
        assert _value_to_score('Bon', m) == 3
        assert _value_to_score('Optimal', m) == 5

    def test_libelle_inconnu_ou_vide(self):
        m = _TypeMet('TEXTE', l1='Mauvais', l3='Bon')
        assert _value_to_score('Introuvable', m) is None
        assert _value_to_score('', m) is None
        assert _value_to_score(None, m) is None


class TestValueToScoreChiffre:
    def test_valeur_discrete(self):
        m = _TypeMet('CHIFFRE', v1=1, v2=2, v3=3, v4=5, v5=8)
        assert _value_to_score('2', m) == 2
        assert _value_to_score(8, m) == 5

    def test_valeur_hors_grille(self):
        m = _TypeMet('CHIFFRE', v1=1, v2=2, v5=8)
        assert _value_to_score('4', m) is None
        assert _value_to_score('', m) is None
