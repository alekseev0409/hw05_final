from datetime import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    year = datetime.now().year
    dict_ret = {}
    dict_ret['year'] = year
    return dict_ret
