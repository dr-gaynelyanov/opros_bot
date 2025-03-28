## Инструкция для администратора бота опросов

### 1. Получение прав администратора

*   Для получения прав администратора необходимо, чтобы другой администратор добавил вас в список администраторов.
*   Для назначения первого администратора необходимо сначала зарегистрироваться через /start, затем воспользоваться командой /initialize_admin. Эта команда назначит текущего пользователя админом.
*   Для назначения нового администратора существующий должен использовать команду `/admin` и выбрать пункт "Добавить администратора".
*   Администратору потребуется ваш Telegram ID. Его можно узнать, переслав сообщение боту @getidsbot.

### 2. Панель управления администратора

*   Для вызова панели управления администратора используйте команду `/admin`.
*   В панели управления доступны следующие функции:
    *   **Добавить администратора**: Позволяет добавить нового администратора.
    *   **Удалить администратора**: Позволяет удалить существующего администратора.
    *   **Список администраторов**: Позволяет просмотреть список всех администраторов.

*    В панели по команде /start доступны следующие функции:
    *   **Запустить опрос**: Позволяет выбрать и запустить существующий опрос.
    *   **Создать опрос**: Позволяет создать новый опрос.

### 3. Запуск опроса

*   Выберите пункт "Запустить опрос" в панели управления администратора.
*   Выберите опрос из списка доступных опросов.
*   После выбора опроса бот предоставит код доступа к опросу. Этот код необходимо сообщить пользователям для участия в опросе.
*   Пользователи, уже прошедшие опрос, не смогут присоединиться к нему повторно.
*   Нажмите кнопку "Отправить первый вопрос", чтобы начать рассылку вопросов пользователям.

### 4. Создание опроса

*   Выберите пункт "Создать опрос" в панели управления администратора.
*   Введите название опроса.
*   Введите описание опроса.
*   После создания опроса вам будет предложено добавить вопросы с помощью текстового фалйа

#### Формат файла с вопросами

*   Каждый вопрос должен начинаться с номера, за которым следует точка и пробел.
*   Варианты ответов должны начинаться с `+ ` (для правильных ответов) или `- ` (для неправильных ответов).
*   Вопросы должны быть разделены пустыми строками.

**Пример:**

```
1. Столица России?
+ Москва
- Санкт-Петербург
- Казань

2. Какая река самая длинная в мире?
- Нил
+ Амазонка
- Янцзы
```

### 5. Управление вопросами во время опроса

*   После отправки первого вопроса пользователям, администратору будет предоставлена информация о вопросе и кнопка "Завершить прием ответов по вопросу".
*   После нажатия кнопки "Завершить прием ответов по вопросу" пользователям будет отправлено уведомление о завершении приема ответов на текущий вопрос и правильно ли они ответили на вопрос.
*   После завершения приема ответов на текущий вопрос, администратору будет предложено перейти к следующему вопросу.

### 6. Получение результатов опроса

*   После завершения опроса администратору будет автоматически отправлен Excel-файл с результатами опроса.
*   Файл содержит два листа:
    *   **Poll Description**: Содержит информацию об опросе (название, описание, количество вопросов, вопросы и варианты ответов).
    *   **Poll Results**: Содержит результаты опроса по каждому пользователю (ID пользователя, имя пользователя, итоговый балл, ответы на вопросы, правильные ответы).
    *   **Расчет баллов**: Баллы за ответ на вопрос рассчитываются следующим образом: за каждый правильный ответ пользователю начисляется вес этого ответа, а за неправильный ответ баллы вычитаются.
