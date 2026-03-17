# Практический пример работы с Review

## Шаг 1: Первая книга (интерактивная проверка)

```bash
# Обработать первую книгу
python -m book_normalizer.cli process books/book1.txt --interactive
```

**Система показывает проблемы одну за другой**:

```
═══════════════════════════════════════
Issue 1 of 5
Chapter: "Глава 1"
Type: punctuation (high severity)
═══════════════════════════════════════
Context: "Еще один пример,, с двойной"
Original: ,,
Suggested: ,
═══════════════════════════════════════
[1] Accept  [2] Reject  [3] Skip  [4] Edit  [5] Exit
Your choice: 1
```

✅ Ты выбрал **Accept** - система запомнила: `,,` → `,`

```
═══════════════════════════════════════
Issue 2 of 5
Chapter: "Глава 3"
Type: ocr_artifact (high severity)
═══════════════════════════════════════
Context: "Цифры вместо букв: м0сква"
Original: 0
Suggested: о
═══════════════════════════════════════
[1] Accept  [2] Reject  [3] Skip  [4] Edit  [5] Exit
Your choice: 1
```

✅ Ты выбрал **Accept** - система запомнила: `0` → `о`

```
═══════════════════════════════════════
Issue 3 of 5
Chapter: "Глава 5"
Type: spelling (medium severity)
═══════════════════════════════════════
Context: "встрчстврнстй (только согласн"
Original: встрчстврнст
Suggested: (empty)
═══════════════════════════════════════
[1] Accept  [2] Reject  [3] Skip  [4] Edit  [5] Exit
Your choice: 4
```

✏️ Ты выбрал **Edit** - система попросит ввести правильный вариант:
```
Enter replacement text: встречественности
```

✅ Система запомнила: `встрчстврнст` → `встречественности`

---

## Шаг 2: Система сохранила решения

### Файл: data/user_memory/punctuation_memory.json
```json
{
  "entries": [
    {
      "original": ",,",
      "replacement": ",",
      "confirmed": true,
      "count": 1,
      "last_seen": "2026-03-11T22:30:00Z"
    }
  ]
}
```

### Файл: data/user_memory/correction_memory.json
```json
{
  "entries": [
    {
      "original": "0",
      "replacement": "о",
      "confirmed": true,
      "count": 1,
      "last_seen": "2026-03-11T22:30:00Z"
    },
    {
      "original": "встрчстврнст",
      "replacement": "встречественности",
      "confirmed": true,
      "count": 1,
      "last_seen": "2026-03-11T22:30:05Z"
    }
  ]
}
```

---

## Шаг 3: Вторая книга (автоматическое применение)

```bash
# Обработать вторую книгу БЕЗ интерактива
python -m book_normalizer.cli process books/book2.txt
```

**Вывод**:
```
Processing: books\book2.txt
Loaded: 1 chapter(s), source=txt
Normalization complete.
Chapter detection complete: 3 chapter(s) found.
Punctuation detector found 8 issue(s).
OCR/spelling detector found 5 issue(s).
Review session created: 13 total, 3 auto-resolved, 10 pending.
                                  ^^^ АВТОМАТИЧЕСКИ ИСПРАВЛЕНО! ^^^

Found 10 issue(s) requiring review.
Run with --interactive to review issues, or they will be skipped.
```

**Что произошло**:
- Система нашла **13 проблем** в book2.txt
- **3 проблемы** (`,,`, `0`, `встрчстврнст`) были автоматически исправлены
- **10 проблем** остались для ручной проверки (новые, неизвестные)

---

## Шаг 4: Проверка автоматических исправлений

Можно посмотреть, что было исправлено автоматически:

```bash
cat data/user_memory/review_sessions/session_*.json | jq .resolved_issues
```

**Результат**:
```json
[
  {
    "id": "abc123",
    "issue_type": "punctuation",
    "original_fragment": ",,",
    "suggested_fragment": ",",
    "resolved": true
  },
  {
    "id": "def456",
    "issue_type": "ocr_artifact",
    "original_fragment": "0",
    "suggested_fragment": "о",
    "resolved": true
  },
  {
    "id": "ghi789",
    "issue_type": "spelling",
    "original_fragment": "встрчстврнст",
    "suggested_fragment": "встречественности",
    "resolved": true
  }
]
```

---

## Итог

✅ **Первая книга**: Проверяешь вручную, принимаешь решения
✅ **Система запоминает**: Все твои решения сохраняются
✅ **Следующие книги**: Автоматически применяются знакомые исправления
✅ **Экономия времени**: Каждую ошибку нужно исправить только ОДИН РАЗ!

---

## Дополнительные команды

### Посмотреть память
```bash
# Пунктуация
cat data/user_memory/punctuation_memory.json | jq .

# Исправления
cat data/user_memory/correction_memory.json | jq .
```

### Очистить память (если нужно начать заново)
```bash
rm data/user_memory/punctuation_memory.json
rm data/user_memory/correction_memory.json
```

### Посмотреть статистику
```bash
# Сколько исправлений в памяти
cat data/user_memory/correction_memory.json | jq '.entries | length'

# Самые частые исправления
cat data/user_memory/correction_memory.json | jq '.entries | sort_by(.count) | reverse | .[0:5]'
```
