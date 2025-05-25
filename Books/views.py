from django.http import JsonResponse
from django.views import View
from .models import BorrowRequest
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from Books.forms import BorrowRequestAdminForm
from Books.models import Book


@login_required
def borrow_book(request):
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        book = get_object_or_404(Book, id=book_id)

        form_data = {
            'user': request.user.id,
            'book': book.id
        }

        form = BorrowRequestAdminForm(data=form_data)
        if form.is_valid():
            form.save()
            messages.success(request, 'Вы успешно встали в очередь!')
        else:
            messages.error(request, 'Не удалось встать в очередь. Попробуйте позже.')

        return redirect(request.META.get('HTTP_REFERER', '/'))  # Перенаправляем обратно

    return redirect('/')
