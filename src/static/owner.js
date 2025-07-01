document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();

    const calendarContainer = document.getElementById('calendar-container');
    const loader = document.getElementById('loader');
    const urlParams = new URLSearchParams(window.location.search);
    const propertyId = urlParams.get('property_id');
    
    if (!propertyId) {
        calendarContainer.innerHTML = '<p style="color: red;">Ошибка: ID объекта не указан в URL.</p>';
        return;
    }

    let currentYear, currentMonth;
    let calendarData = {};
    let selection = { start: null, end: null };
    let isLoading = false;
    const monthNames = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];
    const dayNames = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

    // ... (функции fetchAndRenderMonth, renderMonth, updateSelectionHighlight без изменений)
    async function fetchAndRenderMonth(year, month) { /* ... */ }
    function renderMonth(year, month) { /* ... */ }
    function updateSelectionHighlight() {
        document.querySelectorAll('.day-cell[data-date]').forEach(cell => {
            const cellDate = new Date(cell.dataset.date + 'T00:00:00');
            const inSelection = selection.start && cellDate >= selection.start && (selection.end || selection.start) && cellDate <= (selection.end || selection.start);
            cell.classList.toggle('selected', inSelection);
        });
    }

    // --- ИЗМЕНЕНИЕ: Полностью новая логика выделения ---
    calendarContainer.addEventListener('click', (e) => {
        const cell = e.target.closest('.day-cell');
        if (!cell || !cell.dataset.date || cell.classList.contains('disabled')) return;
        
        const clickedDate = new Date(cell.dataset.date + 'T00:00:00');

        // Если это первый клик или мы начинаем новое выделение
        if (!selection.start || selection.end) {
            selection.start = clickedDate;
            selection.end = null;
            updateSelectionHighlight();
        } 
        // Если это второй клик
        else {
            // Если кликнули на ту же дату (действие для одной даты)
            if (clickedDate.getTime() === selection.start.getTime()) {
                selection.end = clickedDate; // Завершаем выделение на одной дате
                showActionPopup();
            } 
            // Если кликнули на другую дату (действие для периода)
            else {
                if (clickedDate < selection.start) {
                    selection.end = selection.start;
                    selection.start = clickedDate;
                } else {
                    selection.end = clickedDate;
                }
                showActionPopup();
            }
            updateSelectionHighlight();
        }
    });

    window.addEventListener('scroll', () => { /* ... */ });

    // ... (остальные функции handlePopupAction, setPeriodAvailability, handleSetPrice, main без изменений)
    function showActionPopup() {
        if (!selection.start) return;
        const isSingleDate = !selection.end || selection.start.getTime() === selection.end.getTime();
        const startDateStr = selection.start.toLocaleDateString('ru-RU');
        const endDateStr = selection.end.toLocaleDateString('ru-RU');
        const message = isSingleDate ? `Применить действие для даты: ${startDateStr}` : `Применить действие для периода: ${startDateStr} - ${endDateStr}`;

        tg.showPopup({
            title: 'Управление датами',
            message: message,
            buttons: [
                { id: 'block', type: 'default', text: '🚫 Заблокировать' },
                { id: 'unblock', type: 'default', text: '✅ Сделать доступными' },
                { id: 'set_price', type: 'default', text: '💰 Установить цену' },
                { type: 'cancel' },
            ]
        }, (buttonId) => handlePopupAction(buttonId));
    }
    
    function handlePopupAction(buttonId) {
        if (!buttonId) {
            selection.start = null;
            selection.end = null;
            updateSelectionHighlight();
            return;
        }
        switch (buttonId) {
            case 'block':
                const comment = prompt("Введите причину блокировки (необязательно):", "");
                if (comment !== null) setPeriodAvailability(false, comment);
                break;
            case 'unblock':
                setPeriodAvailability(true, null);
                break;
            case 'set_price':
                handleSetPrice();
                break;
        }
    }

    async function setPeriodAvailability(isAvailable, comment) {
        const dates = [];
        const endDate = selection.end || selection.start;
        for (let d = new Date(selection.start); d <= endDate; d.setDate(d.getDate() + 1)) {
            dates.push(d.toISOString().split('T')[0]);
        }
        
        setLoaderVisible(true);
        try {
            const response = await fetch(`/api/owner/set_availability`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    property_id: propertyId, 
                    dates: dates, 
                    is_available: isAvailable,
                    comment: comment
                })
            });
            if (!response.ok) throw new Error('Ошибка сервера.');
            tg.showPopup({ title: 'Успех', message: `Статус для выбранного периода успешно изменен.` });
        } catch (error) {
            tg.showAlert(`Ошибка: ${error.message}`);
        } finally {
            selection.start = null;
            selection.end = null;
            calendarContainer.innerHTML = '';
            main();
        }
    }

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
            const response = await fetch(`/api/owner/price_rule`, {
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
            tg.showPopup({ title: 'Успех', message: `Цена ${price}₽ установлена для периода с ${startDate} по ${endDate}.` });
        } catch (error) {
            tg.showAlert(`Ошибка: ${error.message}`);
        } finally {
            selection.start = null;
            selection.end = null;
            calendarContainer.innerHTML = '';
            main();
        }
    }

    async function main() {
        const today = new Date();
        currentYear = today.getFullYear();
        currentMonth = today.getMonth();
        for (let i = 0; i < 4; i++) {
            let yearToLoad = currentYear;
            let monthToLoad = currentMonth + i;
            if (monthToLoad > 11) {
                yearToLoad += Math.floor(monthToLoad / 12);
                monthToLoad = monthToLoad % 12;
            }
            await fetchAndRenderMonth(yearToLoad, monthToLoad);
        }
    }
    main();
});