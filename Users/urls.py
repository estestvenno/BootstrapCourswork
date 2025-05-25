from django.urls import path
from .views import indexView, registerView, loginView, homeView, update_profileView, \
    change_passwordView  # Import the view here

urlpatterns = [
    path('', indexView, name='index'),
    path('home/', homeView, name='home'),
    path('login/', loginView.as_view(), name='login'),
    path('register/', registerView.as_view(), name='register'),
    path('update_profile/', update_profileView, name='update_profile'),
    path('change-password/', change_passwordView, name='change_password'),
]
