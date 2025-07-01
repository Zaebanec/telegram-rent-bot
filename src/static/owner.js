document.addEventListener('DOMContentLoaded', () => {
    // Инициализация Telegram Web App
    const tg = window.Telegram.WebApp;
    tg.expand();

    // --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ И ЭЛЕМЕНТЫ DOM ---
    const calendarGrid = document.getElementById('calendar-grid');
    const monthYearHeader = document.getElementById('month-year');
    const prevMonthBtn = document.getElementById('prev-month');
    const nextMonthBtn = document.getElementById('next-month');
    const loader = document.getElementById('loader');

    // Извлекаем property_id из URL
    const urlParams = new URLSearchParams(window.location.search);
    const propertyId = urlParams.get('property_id');

    // Если ID объекта не найден, показываем ошибку
    if (!propertyId) {
        calendarGrid.innerHTML = '<p style="color: red; grid-column: 1 / 8;">Ошибка: ID объекта не указан в URL.</p>';
        return;
    }

    // Состояние приложения
    let current = new Date();
    let selection = { start: null, end: null };
    let isMouseDown = false;
    // URL вашего сервера (замените на реальный, если он отличается)
    const API_BASE_URL = ''; 


    // --- ОСНОВНЫЕ ФУНКЦИИ ---

    /**
     * Показывает или скрывает индикатор загрузки
     * @param {boolean} visible - Показать (true) или скрыть (false)
     */
    function setLoaderVisible(visible) {
        if (visible) {
            loader.classList.add('visible');
        } else {
            loader.classList.remove('visible');
        }
    }

    /**
     * Запрашивает данные календаря с сервера
     * @param {number} year - Год
     * @param {number} month - Месяц (1-12)
     */
    async function fetchAndRenderCalendar(year, month) {
        setLoaderVisible(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/calendar_data/${propertyId}?year=${year}&month=${month}`);
            if (!response.ok) {
                throw new Error(`Ошибка сети: ${response.statusText}`);
            }
            const data = await response.json();
            renderCalendar(year, month, data);
        } catch (error) {
            console.error('Не удалось загрузить данные календаря:', error);
            tg.showAlert(`Ошибка загрузки данных: ${error.message}`);
        } finally {
            setLoaderVisible(false);
        }
    }

    /**
     * Отрисовывает календарь на основе полученных данных
     * @param {number} year - Год
     * @param {number} month - Месяц (1-12)
     * @param {Array} daysData - Массив данных о днях
     */
    function renderCalendar(year, month, daysData) {
        monthYearHeader.textContent = new Date(year, month - 1).toLocaleString('ru-RU', { month: 'long', year: 'numeric' });
        
        // Очищаем предыдущие ячейки
        const dayCells = calendarGrid.querySelectorAll('.day-cell');
        dayCells.forEach(cell => cell.remove());

        const firstDayOfMonth = new Date(year, month - 1, 1).getDay();
        const daysInMonth = new Date(year, month, 0).getDate();
        // Корректируем, чтобы неделя начиналась с понедельника (0 = Пн, 6 = Вс)
        const dayOfWeekOffset = (firstDayOfMonth === 0) ? 6 : firstDayOfMonth - 1;

        // Добавляем пустые ячейки для дней предыдущего месяца
        for (let i = 0; i < dayOfWeekOffset; i++) {
            const emptyCell = document.createElement('div');
            emptyCell.className = 'day-cell empty';
            calendarGrid.appendChild(emptyCell);
        }

        // Добавляем ячейки для каждого дня месяца
        daysData.forEach(day => {
            const cell = document.createElement('div');
            cell.className = 'day-cell';
            cell.dataset.date = day.date; // e.g., "2024-12-25"

            // Номер дня
            const dayNumber = document.createElement('span');
            dayNumber.className = 'day-number';
            dayNumber.textContent = new Date(day.date).getDate();
            cell.appendChild(dayNumber);

            // Цена (если есть)
            if (day.price !== null) {
                const dayPrice = document.createElement('span');
                dayPrice.className = 'day-price';
                dayPrice.textContent = `${day.price}₽`;
                cell.appendChild(dayPrice);
            }
            
            // Комментарий (если есть)
            if (day.comment) {
                const dayComment = document.createElement('span');
                dayComment.className = 'day-comment';
                dayComment.textContent = '●';
                dayComment.title = day.comment; // Всплывающая подсказка
                cell.appendChild(dayComment);
            }

            // Добавляем классы в зависимости от статуса
            cell.classList.add(day.status);
            
            // Если дата уже выбрана, подсвечиваем ее
            if (isDateInSelection(new Date(day.date))) {
                 cell.classList.add('selected');
            }

            calendarGrid.appendChild(cell);
        });
    }

    /**
     * Проверяет, находится ли дата в текущем выделенном диапазоне
     */
    function isDateInSelection(date) {
        if (!selection.start) return false;
        const normalizedDate = new Date(date.setHours(0,0,0,0));
        const startDate = new Date(selection.start.setHours(0,0,0,0));
        const endDate = selection.end ? new Date(selection.end.setHours(0,0,0,0)) : startDate;

        return normalizedDate >= startDate && normalizedDate <= endDate;
    }
    
    /**
     * Обновляет подсветку выделенных ячеек
     */
    function updateSelectionHighlight() {
        document.querySelectorAll('.day-cell[data-date]').forEach(cell => {
            const cellDate = new Date(cell.dataset.date + 'T00:00:00'); // Устанавливаем время для корректного сравнения
            if (isDateInSelection(cellDate)) {
                cell.classList.add('selected');
            } else {
                cell.classList.remove('selected');
            }
        });
    }


    // --- ОБРАБОТЧИКИ СОБЫТИЙ ---

    // Клик на кнопку "Предыдущий месяц"
    prevMonthBtn.addEventListener('click', () => {
        current.setMonth(current.getMonth() - 1);
        fetchAndRenderCalendar(current.getFullYear(), current.getMonth() + 1);
    });

    // Клик на кнопку "Следующий месяц"
    nextMonthBtn.addEventListener('click', () => {
        current.setMonth(current.getMonth() + 1);
        fetchAndRenderCalendar(current.getFullYear(), current.getMonth() + 1);
    });

    // --- ЛОГИКА ВЫДЕЛЕНИЯ ДАТ ---

    calendarGrid.addEventListener('mousedown', (e) => {
        const cell = e.target.closest('.day-cell');
        if (!cell || !cell.dataset.date || cell.classList.contains('past') || cell.classList.contains('booked')) return;
        
        isMouseDown = true;
        const clickedDate = new Date(cell.dataset.date + 'T00:00:00');
        
        // Логика сброса/установки выделения
        if (selection.start && !selection.end && clickedDate.getTime() === selection.start.getTime()){
            // Клик на уже выделенную единственную дату - снимает выделение
            selection.start = null;
        } else if (selection.start && selection.end) {
             // Если был выделен диапазон, сбрасываем и начинаем новый
             selection.start = clickedDate;
             selection.end = null;
        } else {
            // Начинаем выделение
            selection.start = clickedDate;
            selection.end = null;
        }
        
        updateSelectionHighlight();
        showActionPopup();
    });

    calendarGrid.addEventListener('mouseover', (e) => {
        if (!isMouseDown || !selection.start) return;
        const cell = e.target.closest('.day-cell');
        if (!cell || !cell.dataset.date || cell.classList.contains('past') || cell.classList.contains('booked')) return;

        const hoverDate = new Date(cell.dataset.date + 'T00:00:00');
        
        // Устанавливаем конец диапазона, обеспечивая правильный порядок дат
        if (hoverDate >= selection.start) {
            selection.end = hoverDate;
        } else {
            // Если ведем мышь назад, начальная дата становится конечной
            selection.end = selection.start;
            selection.start = hoverDate;
        }
        updateSelectionHighlight();
    });
    
    // Отпускаем кнопку мыши в любом месте окна
    window.addEventListener('mouseup', () => {
        if (isMouseDown) {
            isMouseDown = false;
            // Если выделение не сброшено, показываем меню действий
            if (selection.start) {
                showActionPopup();
            }
        }
    });

    // --- ФУНКЦИИ ДЕЙСТВИЙ С ДАТАМИ ---
    
    /**
     * Показывает всплывающее окно с действиями для выделенных дат
     */
    function showActionPopup() {
        if (!selection.start) return;

        const isSingleDate = !selection.end || selection.start.getTime() === selection.end.getTime();
        const targetDate = selection.start;
        const dateString = targetDate.toLocaleDateString('ru-RU');
        
        const cell = document.querySelector(`.day-cell[data-date='${targetDate.toISOString().split('T')[0]}']`);
        const currentStatus = cell ? (cell.classList.contains('manual-block') ? 'manual_block' : 'available') : 'available';

        if (isSingleDate) {
            // --- Меню для одной даты ---
            const actionText = currentStatus === 'manual_block' ? `Разблокировать ${dateString}` : `Заблокировать ${dateString}`;
            const commentText = currentStatus === 'manual_block' ? ` (комментарий: ${cell.querySelector('.day-comment')?.title || 'нет'})` : '';

            tg.showPopup({
                title: 'Действие с датой',
                message: `Выбрана дата: ${dateString}${commentText}.`,
                buttons: [
                    { id: 'toggle_block', type: 'default', text: actionText },
                    { id: 'set_price', type: 'default', text: 'Установить цену' },
                    { type: 'cancel' },
                ]
            }, (buttonId) => handlePopupAction(buttonId));

        } else {
            // --- Меню для диапазона ---
            const startDateStr = selection.start.toLocaleDateString('ru-RU');
            const endDateStr = selection.end.toLocaleDateString('ru-RU');

            tg.showPopup({
                title: 'Действия с диапазоном',
                message: `Выбран диапазон: ${startDateStr} - ${endDateStr}.`,
                buttons: [
                    { id: 'set_price_range', type: 'default', text: 'Установить цену' },
                    { type: 'cancel' },
                ]
            }, (buttonId) => handlePopupAction(buttonId));
        }
    }
    
    /**
     * Обрабатывает выбор в кастомном popup
     */
    function handlePopupAction(buttonId) {
        if (!buttonId) { // Если закрыли popup без выбора
            selection.start = null;
            selection.end = null;
            updateSelectionHighlight();
            return;
        }
        
        switch (buttonId) {
            case 'toggle_block':
                handleToggleBlock();
                break;
            case 'set_price':
            case 'set_price_range':
                handleSetPrice();
                break;
        }
    }

    /**
     * Обрабатывает блокировку/разблокировку даты
     */
    async function handleToggleBlock() {
        const dateToToggle = selection.start.toISOString().split('T')[0];
        const cell = document.querySelector(`.day-cell[data-date='${dateToToggle}']`);
        const isBlocking = !cell.classList.contains('manual-block');
        let comment = null;

        if (isBlocking) {
            // Вместо showPopup используем нативный prompt, который работает везде
            comment = prompt("Введите причину блокировки (необязательно):", "");
        }

        setLoaderVisible(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/owner/toggle_availability`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ property_id: propertyId, date: dateToToggle, comment: comment })
            });
            if (!response.ok) throw new Error('Ошибка сервера при блокировке даты.');
            tg.showPopup({title: 'Успех', message: `Дата ${dateToToggle} успешно ${isBlocking ? 'заблокирована' : 'разблокирована'}.`});
        } catch (error) {
            tg.showAlert(`Ошибка: ${error.message}`);
        } finally {
            selection.start = null;
            selection.end = null;
            fetchAndRenderCalendar(current.getFullYear(), current.getMonth() + 1); // Перерисовываем календарь
        }
    }

    /**
     * Обрабатывает установку цены
     */
    async function handleSetPrice() {
        const price = prompt("Введите новую цену для выбранного периода:", "5000");
        if (price === null || isNaN(parseInt(price)) || parseInt(price) <= 0) {
            if (price !== null) tg.showAlert("Пожалуйста, введите корректное число больше нуля.");
            selection.start = null;
            selection.end = null;
            updateSelectionHighlight();
            return;
        }

        const startDate = selection.start.toISOString().split('T')[0];
        const endDate = (selection.end || selection.start).toISOString().split('T')[0];
        
        setLoaderVisible(true);
        try {
            const response = await fetch(`${API_BASE_URL}/api/owner/price_rule`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    property_id: propertyId,
                    start_date: startDate,
                    end_date: endDate,
                    price: parseInt(price)
                })
            });
            if (!response.ok) throw new Error('Ошибка сервера при установке цены.');
             tg.showPopup({title: 'Успех', message: `Цена ${price}₽ установлена для периода с ${startDate} по ${endDate}.`});
        } catch(error) {
            tg.showAlert(`Ошибка: ${error.message}`);
        } finally {
            selection.start = null;
            selection.end = null;
            fetchAndRenderCalendar(current.getFullYear(), current.getMonth() + 1);
        }
    }

    // --- ПЕРВЫЙ ЗАПУСК ---
    fetchAndRenderCalendar(current.getFullYear(), current.getMonth() + 1);
});

