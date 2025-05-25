from django.utils import timezone
from .models import BorrowRequest, BookCopy


def update_borrow_queue(book):
    """
    Обновляет очередь на книгу: если есть свободные копии,
    переводит первых в очереди в статус 'pending'.

    :param book: объект модели Book
    """
    total_copies = BookCopy.objects.filter(book=book).count()

    if total_copies == 0:
        return

    active_borrows = BorrowRequest.objects.filter(
        book=book,
        status='approved'
    ).count()

    available_slots = max(0, total_copies - active_borrows)

    if available_slots <= 0:
        return

    queued_requests = BorrowRequest.objects.filter(
        book=book,
        status='in_queue'
    ).order_by('requested_at')[:available_slots]

    for request in queued_requests:
        request.status = 'pending'
        request.save()