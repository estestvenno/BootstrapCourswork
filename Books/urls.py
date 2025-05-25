from django.urls import path
from .views import borrow_book

urlpatterns = [
    path('borrow-book/', borrow_book, name='borrow_book'),
]
