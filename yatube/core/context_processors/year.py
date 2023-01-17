from datetime import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    dt = datetime.now()
    return {
        'year': dt.year
    }
