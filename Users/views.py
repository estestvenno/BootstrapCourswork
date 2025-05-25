import random

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.db.models import Q
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordChangeView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View  # Импорт базового класса для создания классовых представлений
from django.contrib.auth.views import LoginView  # Импорт встроенного класса для авторизации
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from Books.models import Book, Author, BorrowRequest
import logging

from Users.models import Profile

logger = logging.getLogger(__name__)


def indexView(request):
    if request.user.is_authenticated:
        return redirect('home')  # Имя пути для home
    else:
        books = Book.objects.all()
        authors = Author.objects.all()
        all_books = list(books)
        random.shuffle(all_books)
        first_half = all_books[:100]

        return render(request, 'Users/index.html',
                      {'books': books, 'authors': authors, 'carousel_one_books': first_half, })


@login_required
def homeView(request):
    query = request.GET.get('q', '').strip()

    # Получаем все книги
    books = Book.objects.all()

    # Фильтруем, если есть запрос
    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(authors__name__icontains=query)
        ).distinct()

    # Разбиваем на две части случайно (для каруселей)
    all_books = list(books)
    random.shuffle(all_books)
    first_half = all_books[:100]

    # Все авторы — остаются без изменений
    authors = Author.objects.all()
    query = query[:100]

    borrow_requests = BorrowRequest.objects.filter(
        status__in=['pending', 'in_queue']
    ).order_by('requested_at')  # от самого старого к самому новому

    borrow_requests_user = BorrowRequest.objects.filter(
        user=request.user  # <-- теперь фильтруем именно по пользователю
    ).order_by('-requested_at')  # от самого старого к самому новому

    return render(request, 'Users/home.html', {
        'books': first_half,
        'authors': authors,
        'query': query,
        'borrow_requests': borrow_requests,
        'borrow_requests_user': borrow_requests_user,
    })


class loginView(View):  # Наследование от встроенного класса LoginView
    def get(self, request):
        return render(request, 'registration/login.html')

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')  # 'remember-me' или None

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Если пользователь поставил галочку "Remember me"
            if remember:
                request.session.set_expiry(1209600)  # 2 недели в секундах
            else:
                request.session.set_expiry(0)  # Сессия будет удалена при закрытии браузера
            request.session.modified = True

            return redirect('home')  # замени 'home' на нужный URL-путь
        else:
            # Обработка ошибки: неверные учетные данные
            return render(request, 'registration/login.html', {
                'error': 'Invalid username or password'
            })


class registerView(View):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(to='/')
        return super(registerView, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, 'registration/register.html')

    def post(self, request):
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        remember = request.POST.get('remember')  # 'remember' или None

        error = None

        if not username or not password1 or not password2:
            error = 'All fields are required.'
        elif password1 != password2:
            error = 'Passwords do not match.'
        elif User.objects.filter(username=username).exists():
            error = 'Username already exists.'

        if error:
            return render(request, 'registration/register.html', {
                'error': error,
                'username': username  # Сохраняем введённый никнейм
            })

        # Создаем пользователя
        user = User.objects.create_user(username=username, password=password1)
        user.save()

        # Логиним пользователя после регистрации
        login(request, user)

        # Обработка "Remember me"
        if remember:
            request.session.set_expiry(1209600)  # 2 недели
        else:
            request.session.set_expiry(0)  # Сессия закроется с браузером
        request.session.modified = True

        return redirect('home')  # заменить на нужный URL


class CustomLogoutView(LogoutView):
    template_name = 'Users/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if not self.request.user.is_authenticated:
            books = Book.objects.all()
            all_books = list(books)
            random.shuffle(all_books)
            half = len(all_books) // 2
            first_half = all_books[:half]
            second_half = all_books[half:]

            context.update({
                'books': books,
                'authors': Author.objects.all(),
                'carousel_one_books': first_half,
                'carousel_two_books': second_half,
            })

        return context

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        return redirect('index')


@login_required
def update_profileView(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        avatar = request.FILES.get('avatar')

        user = request.user

        # Обновляем поля пользователя
        if username:
            user.username = username
        user.save()

        # Получаем или создаём профиль
        profile, created = Profile.objects.get_or_create(user=user)

        # Обновляем аватар, если он передан
        if avatar:
            profile.avatar = avatar
        profile.save()  # Вызов save() здесь вызовет ваш кастомный save() в модели

        messages.success(request, "Профиль успешно обновлён.")
        return redirect('home')  # или куда нужно перенаправить

    return redirect('home')


@login_required
def change_passwordView(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')

        user = request.user

        # Проверяем старый пароль
        if not user.check_password(old_password):
            messages.error(request, "Старый пароль указан неверно.")
            return redirect('home')  # или редирект обратно в профиль

        # Проверяем совпадение новых паролей
        if new_password1 != new_password2:
            messages.error(request, "Новые пароли не совпадают.")
            return redirect('home')

        # Проверяем длину пароля
        if len(new_password1) < 8:
            messages.error(request, "Пароль должен содержать минимум 8 символов.")
            return redirect('home')

        # Меняем пароль
        user.set_password(new_password1)
        user.save()

        messages.success(request, "Ваш пароль успешно изменён.")
        return redirect('home')

    return redirect('home')
