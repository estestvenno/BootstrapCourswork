# admin.py
from django.contrib import admin

from django.contrib import messages
from Books.forms import BorrowRequestAdminForm
from .models import Author, Genre, Book, BookCopy, BorrowHistory
from .services import update_borrow_queue


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display = ('book', 'copy_id', 'is_available', 'damaged')
    list_filter = ('is_available', 'damaged', 'book__genre')
    search_fields = ('book__title', 'copy_id')
    readonly_fields = ('copy_id',)


class BookCopyInline(admin.TabularInline):
    model = BookCopy
    extra = 1  # Показывает одно пустое поле для добавления нового экземпляра


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'year', 'isbn13', 'has_available_copies', 'get_authors', 'genre')
    list_filter = ('genre', 'year', 'authors')
    search_fields = ('title', 'isbn13', 'description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [BookCopyInline]

    def get_authors(self, obj):
        return ", ".join([author.name for author in obj.authors.all()])

    get_authors.short_description = 'Авторы'

    def has_available_copies(self, obj):
        return obj.has_available_copies

    has_available_copies.boolean = True
    has_available_copies.short_description = 'Доступна'


@admin.register(BorrowHistory)
class BorrowHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'book_title', 'adminAction', 'borrowed_at', 'returned_at', 'due_back')
    list_filter = ('user', 'adminAction', 'borrowed_at')
    search_fields = ('user__username', 'copy__book__title')
    actions = ['delete_selected']  # только удаление

    def book_title(self, obj):
        return obj.copy.book.title

    book_title.short_description = 'Книга'

    # Запретить отображение кнопки "Добавить"
    def has_add_permission(self, request):
        return False

    # Запретить редактирование записей
    def has_change_permission(self, request, obj=None):
        return False

    # Разрешить удаление
    def has_delete_permission(self, request, obj=None):
        return True

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


# admin.py
from datetime import timedelta
from django.utils import timezone
from django.contrib import admin
from .models import BorrowRequest, BookCopy, BorrowHistory


@admin.register(BorrowRequest)
class BorrowRequestAdmin(admin.ModelAdmin):
    form = BorrowRequestAdminForm

    list_display = ('user', 'book_title', 'status', 'requested_at', 'approved_at', 'due_back')
    list_filter = ('status', 'requested_at', 'approved_at', 'user', 'book')
    search_fields = ('user__username', 'book__title')

    readonly_fields = ('status', 'requested_at', 'approved_at', 'due_back')
    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Книга', {
            'fields': ('book',)
        }),
        ('Даты', {
            'fields': ('requested_at', 'approved_at', 'due_back'),
            'classes': ('collapse',)
        }),
        ('Статус', {
            'fields': ('status',)
        }),
    )
    actions = ['approve_requests', 'reject_requests', 'mark_returned']

    # Вспомогательный метод для отображения названия книги в списке
    def book_title(self, obj):
        return obj.book.title
    book_title.short_description = 'Книга'
    book_title.admin_order_field = 'book__title'

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


    def save_model(self, request, obj, form, change):
        if not change:  # Только при создании
            obj.requested_at = timezone.now()

        super().save_model(request, obj, form, change)

    # Одобрить
    def approve_requests(self, request, queryset):
        for req in queryset.filter(status='pending'):
            # Ищем первую доступную копию книги
            available_copy = BookCopy.objects.filter(
                book=req.book,
                is_available=True
            ).first()

            if not available_copy:
                # Нет доступных копий — можно пропустить или перевести в очередь
                self.message_user(request, f"Нет доступных копий для {req.book.title}. Запрос пропущен.")
                continue

            # Одобряем запрос
            req.status = 'approved'
            req.approved_at = timezone.now()
            if not req.due_back:
                req.due_back = timezone.now() + timedelta(days=14)
            req.save()

            # Обновляем статус копии
            available_copy.is_available = False
            available_copy.save()

            # Создаем запись в истории выдачи
            BorrowHistory.objects.create(
                copy=available_copy,
                user=req.user,
                userAdmin=request.user,
                adminAction='approved',
                borrowed_at=timezone.now(),
                due_back=req.due_back
            )

        self.message_user(request, f"{queryset.count()} запрос(ов) одобрено.")
    approve_requests.short_description = "✅ Одобрить выбранные запросы"

    # Отклонить
    def reject_requests(self, request, queryset):
        pending_requests = queryset.filter(status='pending')
        count = pending_requests.count()
        admin_user = request.user

        # Создаём записи в истории для каждого запроса
        for req in pending_requests:
            any_copy = BookCopy.objects.filter(book=req.book).first()
            BorrowHistory.objects.create(
                copy=any_copy,  # Копия не назначалась, так как запрос был отклонён
                user=req.user,
                userAdmin=admin_user,
                adminAction='refused'
            )
            update_borrow_queue(req.book)
        pending_requests.delete()
        self.message_user(request, f"{count} запрос(ов) отклонено и добавлено в историю.")

    reject_requests.short_description = "❌ Отклонить выбранные запросы"

    # Возвращена (удаление записи)
    def mark_returned(self, request, queryset):
        count = 0
        books_to_update = []

        for req in queryset.filter(status='approved'):
            # Ищем последнюю активную запись в истории для этого запроса
            history_entry = BorrowHistory.objects.filter(
                user=req.user,
                copy__book=req.book,
                adminAction='approved',
                returned_at__isnull=True
            ).first()

            if history_entry and history_entry.copy:
                history_entry.returned_at = timezone.now()
                history_entry.adminAction = 'returned'
                history_entry.copy.is_available = True
                history_entry.copy.save()
                history_entry.save()

                books_to_update.append(req.book)
                req.delete()
                count += 1

        # Обновляем очередь
        for book in set(books_to_update):
            update_borrow_queue(book)

        if count == 0:
            self.message_user(request, "Не найдено активных выдач для возврата.", level=messages.WARNING)
        else:
            self.message_user(request, f"{count} книг(а) успешно возвращено(ы).")
    mark_returned.short_description = "📦 Книга возвращена"
