from django import forms
from django.core.exceptions import ValidationError
from Books.models import BorrowRequest, Book, BookCopy


class BorrowRequestAdminForm(forms.ModelForm):
    book = forms.ModelChoiceField(
        queryset=Book.objects.all(),
        label="Книга",
        required=True
    )

    class Meta:
        model = BorrowRequest
        fields = ['user', 'book']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Инициализируем book из текущей книги (через copy, если был)
            if hasattr(self.instance, 'book'):
                self.fields['book'].initial = self.instance.book
            elif self.instance.copy:
                self.fields['book'].initial = self.instance.copy.book

    def save(self, commit=True):
        instance = super().save(commit=False)
        selected_book = self.cleaned_data.get('book')

        if not selected_book:
            raise ValidationError("Не выбрана книга.")

        # Привязываем книгу к заявке
        instance.book = selected_book

        # Проверяем, есть ли вообще копии книги
        all_copies = BookCopy.objects.filter(book=selected_book)
        if not all_copies.exists():
            raise ValidationError("У этой книги нет экземпляров.")

        available_copies_count = all_copies.filter(is_available=True).count()

        # Считаем, сколько сейчас активных pending-заявок на эту книгу
        pending_requests_count = BorrowRequest.objects.filter(
            book=selected_book,
            status='pending'
        ).count()

        # Если есть свободные копии и ещё можно добавить в pending
        if available_copies_count >= pending_requests_count:
            instance.status = 'pending'
        else:
            instance.status = 'in_queue'

        if commit:
            instance.save()
        return instance
