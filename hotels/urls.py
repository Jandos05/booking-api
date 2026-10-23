
from rest_framework.routers import DefaultRouter

from .views import HotelViewSet, RoomViewSet

router = DefaultRouter()
router.register('hotels', HotelViewSet, basename='hotel')
router.register('rooms', RoomViewSet, basename='room')

urlpatterns = router.urls
