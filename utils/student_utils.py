DIRECTION_CHOICES = [
    #Промышленность и автоматизация
    ('asutp', 'Промышленная автоматика'),
    ('roboto', 'Промышленная робототехника'),
    ('kipia', 'Промышленное оборудование. КИПиА'),
    ('zra', 'Промышленное оборудование. Запорно-регулирующая арматура и насосы'),
    ('svarka', 'Промышленное оборудование. Сварочное оборудование'),
    ('chpu', 'Программирование станоков с ЧПУ'),
    ('bez', 'Прромышленная безопасность'),

    #Информационные технологии
    ('piton', 'WEb-программирование'),
    ('1c', 'Бизнес-информатика на платформе 1С'),
    ('bim', 'BIM-проектирование'),
    ('bpla', 'Aэронавигация и проектирование БПЛА'),
    
    #Электроника и электротехника
    ('micro', 'Микроэлектроника'),
    ('electro', 'Электромонтаж и эксплуатация высоковольтного оборудования'),

    #Химия и медицина
    ('himiya', 'Лабораторный химический анализ'),
    ('medicina', 'Лечебное дело и медицинская техника'),
    ('bio', 'Биотехнология'),
    
    #Экономика и управление
    ('econom', 'Экономика и управление проектом'),
    ('urist', 'Юриспруденция и управление рисками'),

    #Педагогика
    ('pedagog', 'Международная педагогика'),
]


DIVISIONS_CHOICES = [
    ('hr', 'Управление HR'),
    ('ssr', 'Служба Стратегического Развития(ССР)'),
    ('ssp', 'Служба Специальных Проектов(ССП)'),
    ('kb', 'Конструкторское Бюро(КБ)'),
    ('srnp', 'Служба Развития Новых Площадок(СРНП)'),
    ('agd', 'Администрация Генерального Директора(АГД)'),
    ('stoitr', 'Стройтрест'),
    ('aldi', 'Алабуга Девелопмент(АЛДИ)'),
    ('economika', 'Управление экономикой'),
    ('invest', 'Управление привлечения инвестиций'),
    ('kapstroy', 'Управление капитального строительства'),
    ('ekspl', 'Управление эксплуатации и энергетики'),
    ('arenda', 'Департамент арендного бизнеса'),
    ('security', 'Служба безопасности и пропускного режима'),
    ('admin_arenda', 'Служба администрирования арендного жилья'),
    ('digital', 'Управление цифровой трансформации'),
    ('edu_admin', 'Служба администрирования образовательного кластера'),
    ('logist', 'Департамент логистики'),
    ('urid', 'Юридическая служба'),
    ('production', 'Производственное подразделение'),
    ('finance', 'Управление финансами'),
    ('central_warehouse', 'Центральный склад'),
    ('residents', 'Управление по взаимодействию с резидентами'),
    ('projects_group', 'Управление группы проектов'),
    ('project_kopty', 'Проект "Копты"'),
    ('kb2', 'Конструкторское бюро №2'),
    ('deputy_office', 'Аппарат заместителя генерального директора'),
    ('corp', 'Департамент по корпоративным вопросам'),
    ('sng', 'Управление по взаимодействию с СНГ'),
    ('mashinnery', 'Машиннери'),
    ('alma', 'АлМа'),
    ('chess', 'Шахматы'),
    ('drake', 'Дрейк'),
    ('siemens', 'Зименс'),
    ('gea', 'ГЭА'),
    ('project_office', 'Проектный офис'),
    ('admin_module', 'Административный модуль'),
    ('acct_tax', 'Управление бухгалтерского и налогового учета'),
]


# helpers for working with choice constants --------------------------------------------------

def normalize_choice_key(val):
    """Return a simplified lowercase string used for comparing values and labels.

    Trims whitespace, lowercases and collapses internal spaces so that
    ``"Промышленная автоматика"`` and ``"промышленная автоматика "``
    will compare equal.
    """
    if not val:
        return ''
    return ' '.join(str(val).strip().lower().split())


def map_choice_value(raw_value, choices, default=None):
    """Given a raw input string return the corresponding key from *choices*.

    The function will match on either the key or the human-readable label.
    Comparison is case‑insensitive and whitespace is normalized.  If nothing
    matches the *default* value (or ``raw_value``) is returned.

    This is useful in import scripts or serializers where end users may supply
    either the machine code (``'asutp'``) or the display name
    (``'Промышленная автоматика'``).
    """
    if raw_value is None:
        return default

    norm = normalize_choice_key(raw_value)
    # try key and label of each choice
    for key, label in choices:
        if norm == normalize_choice_key(key) or norm == normalize_choice_key(label):
            return key
    # fallback to raw_value itself if it's a valid key
    if raw_value in dict(choices):
        return raw_value
    return default
