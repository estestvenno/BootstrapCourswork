from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from Users.views import CustomLogoutView

urlpatterns = [
                  path('admin/', admin.site.urls),

                  path('', include('Users.urls')),
                  path('', include('Books.urls')),
                  path('logout/', CustomLogoutView.as_view(), name='logout'),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
