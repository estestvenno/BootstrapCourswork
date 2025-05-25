from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.utils import timezone


class Author(models.Model):
    name = models.CharField("Имя автора", max_length=100)
    bio = models.TextField("Биография", null=True, blank=True)
    slug = models.SlugField("URL", unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Автор"
        verbose_name_plural = "Авторы"


class Genre(models.Model):
    name = models.CharField("Название жанра", max_length=100)
    description = models.TextField("Описание жанра", null=True, blank=True)
    slug = models.SlugField("URL", unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Жанр"
        verbose_name_plural = "Жанры"


class Book(models.Model):
    title = models.CharField("Название", max_length=255)
    authors = models.ManyToManyField(Author, related_name="books", verbose_name="Авторы")
    isbn13 = models.CharField("ISBN-13", max_length=13, null=True, blank=True)
    description = models.TextField("Описание", null=True, blank=True)
    year = models.PositiveIntegerField("Год издания", null=True, blank=True)
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, related_name="books", verbose_name="Жанр")
    cover = models.ImageField("Обложка", upload_to='covers/', null=True, blank=True)
    slug = models.SlugField("URL", unique=True, blank=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def has_available_copies(self):
        return self.copies.filter(is_available=True).exists()

    class Meta:
        verbose_name = "Книга"
        verbose_name_plural = "Книги"


class BookCopy(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='copies', verbose_name="Книга")
    copy_id = models.CharField("ID экземпляра", max_length=100, unique=True)
    is_available = models.BooleanField("Доступен", default=True)
    damaged = models.BooleanField("Поврежден", default=False)
    notes = models.TextField("Примечания", blank=True)

    def save(self, *args, **kwargs):
        if not self.copy_id:
            copy_id_base = f"{self.book.id}-COPY"
            suffix = 1
            while BookCopy.objects.filter(copy_id=f"{copy_id_base}-{suffix}").exists():
                suffix += 1
            self.copy_id = f"{copy_id_base}-{suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.book.title} - {self.copy_id}"

    class Meta:
        verbose_name = "Экземпляр книги"
        verbose_name_plural = "Экземпляры книг"


class BorrowHistory(models.Model):  # Модель для хранения истории выдачи экземпляров книг
    copy = models.ForeignKey(BookCopy, on_delete=models.CASCADE, related_name='history', verbose_name="Экземпляр")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrowed_books', verbose_name="Пользователь")
    userAdmin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='administered_borrowings',
                                  verbose_name="Админ")
    adminAction = models.CharField(
        max_length=20,
        choices=[
            ('refused', 'Отказано'),
            ('approved', 'Выдана'),
            ('returned', 'Возвращена')
        ],
        verbose_name="Действие Админа"
    )
    borrowed_at = models.DateTimeField("Дата одобрение/отказа", auto_now_add=True, null=True, blank=True)
    returned_at = models.DateTimeField("Дата возврата", null=True, blank=True)
    due_back = models.DateTimeField("Срок возврата", null=True, blank=True)

    def __str__(self):  # Возвращает строковое представление объекта
        return f"{self.user.username} - {self.copy.book.title}"  # Отображает имя пользователя и название книги

    class Meta:  # Настройки модели
        verbose_name = "История выдачи"  # Название модели в интерфейсе (ед. число)
        verbose_name_plural = "Истории выдачи"  # Название модели во множественном числе


class BorrowRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="borrow_requests", verbose_name="Пользователь")
    book = models.ForeignKey('Book', on_delete=models.CASCADE, verbose_name="Книга")
    requested_at = models.DateTimeField(default=timezone.now, verbose_name="Дата запроса")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата выдачи")
    due_back = models.DateTimeField(null=True, blank=True, verbose_name="Ожидаемая дата возврата")
    status = models.CharField(max_length=20, choices=[('pending', 'Ожидает'), ('approved', 'Выдана'), ('in_queue', 'В очереди')], default='in_queue', verbose_name="Статус")


    def __str__(self):
        return f"{self.user} → ({self.status})"

    class Meta:
        ordering = ['requested_at']
        verbose_name = "Запрос на выдачу"
        verbose_name_plural = "Запросы на выдачу"
