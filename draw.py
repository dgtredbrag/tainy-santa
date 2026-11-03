import secrets

def generate_draw(participants: list[str], restrictions: set[tuple[str, str]]):
    """Случайное допустимое взаимно-однозначное распределение.

    Backtracking + эвристика MRV. Возвращает None, если решения нет.
    Для очень больших/плотно ограниченных графов следует перейти на
    специализированный matching solver и ограничить время вычисления.
    """
    if len(participants) < 2 or len(set(participants)) != len(participants):
        return None

    rng = secrets.SystemRandom()
    candidates = {}
    for santa in participants:
        options = [r for r in participants
                   if r != santa and (santa, r) not in restrictions]
        rng.shuffle(options)
        if not options:
            return None
        candidates[santa] = options

    assigned, used = {}, set()

    def search():
        if len(assigned) == len(participants):
            return True

        remaining = [s for s in participants if s not in assigned]
        # MRV: выбираем Санту с минимальным числом оставшихся вариантов.
        santa = min(remaining, key=lambda s: sum(r not in used for r in candidates[s]))
        options = [r for r in candidates[santa] if r not in used]
        rng.shuffle(options)

        for recipient in options:
            assigned[santa] = recipient
            used.add(recipient)
            if search():
                return True
            used.remove(recipient)
            del assigned[santa]
        return False

    return assigned.copy() if search() else None

def validate_draw(participants, restrictions, result):
    return (
        len(result) == len(participants)
        and set(result) == set(participants)
        and set(result.values()) == set(participants)
        and all(s != r and (s, r) not in restrictions for s, r in result.items())
    )
