"""Routes API pour le référentiel CAMPanule."""

from rest_framework.routers import DefaultRouter

from .views import CampanuleViewSet

router = DefaultRouter()
router.register(r'', CampanuleViewSet, basename='campanule')

urlpatterns = router.urls
