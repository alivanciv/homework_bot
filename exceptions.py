class Api400Exception(Exception):

    def __str__(self):
        return 'В запросе передано что-то неожиданное для сервиса.'


class Api401Exception(Exception):

    def __str__(self):
        return 'Запрос с недействительным или некорректным токеном.'


class ApiStatusException(Exception):

    def __str__(self):
        return 'Запрос к API вернул статус код отлтчный от 200'


class HomeworkStatusException(Exception):

    def __str__(self):
        return 'Получен неожиданный статус работы.'
