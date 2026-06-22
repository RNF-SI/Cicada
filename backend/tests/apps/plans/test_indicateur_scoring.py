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
