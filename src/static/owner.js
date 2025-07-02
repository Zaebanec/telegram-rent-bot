document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();
    tg.setHeaderColor('secondary_bg_color');

    // === ИЗМЕНЕНИЕ: Контейнер календаря теперь вложен глубже ===
    const calendarContainer = document.getElementById('calendar-container');
    const calendarWrapper = document.getElementById('calendar-wrapper');

    const loaderOverlay = document.getElementById('loader');
    const actionsContainer = document.getElementById('sticky-actions-container');
    const infoText = document.getElementById('info-text');
    const btnBlock = document.getElementById('action-block');
    const btnUnblock = document.getElementById('action-unblock');
    const btnSetPrice = document.getElementById('action-set-price');

    const urlParams = new URLSearchParams(window.location.search);
    const propertyId = urlParams.get('property_id');
    
    if (!propertyId) {
        calendarContainer.innerHTML = '<p style="color: red; text-align: center; padding-top: 20px;">Ошибка: ID объекта не указан в URL.</p>';
        return;
    }

    let calendarData = {};
    let selection = { start: null, end: null };
    let isLoading = false;
    const monthNames = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];
    const dayNames = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

    function toggleActionsMenu(show) {
        if (show && selection.start && selection.end) {
            const startStr = selection.start.toLocaleDateString('ru-RU', { timeZone: 'UTC' });
            const endStr = selection.end.toLocaleDateString('ru-RU', { timeZone: 'UTC' });
            infoText.textContent = `Период: ${startStr} - ${endStr}`;
            actionsContainer.classList.add('visible');
        } else {
            actionsContainer.classList.remove('visible');
        }
    }

    function resetSelection() {
        selection.start = null;
        selection.end = null;
        updateSelectionHighlight();
        toggleActionsMenu(false);
    }
    
    function isRangeValid(start, end) {
        for (let d = new Date(start); d <= end; d.setUTCDate(d.getUTCDate() + 1)) {
            const dateStr = d.toISOString().split('T')[0];
            const dayData = calendarData[dateStr];
            if (dayData && (dayData.status === 'past' || dayData.status === 'booked')) {
                return false;
            }
        }
        return true;
    }

    calendarContainer.addEventListener('click', (e) => {
        const cell = e.target.closest('.day-cell');
        if (!cell || !cell.dataset.date || cell.classList.contains('disabled')) return;

        const clickedDate = new Date(cell.dataset.date + 'T00:00:00Z');

        if (selection.start && selection.end) {
            resetSelection();
            selection.start = clickedDate;
            updateSelectionHighlight();
            return;
        }

        if (!selection.start) {
            selection.start = clickedDate;
            updateSelectionHighlight();
            return;
        }

        if (selection.start && !selection.end) {
            // === ИЗМЕНЕНИЕ: Без уведомления, просто сброс и новый выбор ===
            if (clickedDate < selection.start) {
                resetSelection();
                selection.start = clickedDate;
                updateSelectionHighlight();
                return;
            }
            
            if (!isRangeValid(selection.start, clickedDate)) {
                tg.showAlert('Выбранный диапазон содержит забронированные или прошедшие даты. Выбор сброшен.', resetSelection);
                return;
            }

            selection.end = clickedDate;
            updateSelectionHighlight();
            toggleActionsMenu(true);
        }
    });
    
    btnBlock.addEventListener('click', () => handlePopupAction('block'));
    btnUnblock.addEventListener('click', () => handlePopupAction('unblock'));
    btnSetPrice.addEventListener('click', () => handlePopupAction('set_price'));

    function setLoaderVisible(visible) {
        loaderOverlay.classList.toggle('visible', visible);
    }
    
    function updateSelectionHighlight() {
        document.querySelectorAll('.day-cell[data-date]').forEach(cell => {
            const cellDate = new Date(cell.dataset.date + 'T00:00:00Z');
            let inSelection = false;
            if (selection.start && !selection.end) {
                inSelection = (cellDate.getTime() === selection.start.getTime());
            } else if (selection.start && selection.end) {
                inSelection = (cellDate >= selection.start && cellDate <= selection.end);
            }
            cell.classList.toggle('selected', inSelection);
        });
    }

    function handlePopupAction(buttonId) {
        switch (buttonId) {
            case 'block':
                tg.showScanQrPopup({ text: 'Причина блокировки (необязательно)' }, (comment) => {
                    setPeriodAvailability(false, comment || null);
                    return true;
                });
                break;
            case 'unblock':
                setPeriodAvailability(true, null);
                break;
            case 'set_price':
                tg.showScanQrPopup({ text: 'Введите новую цену (только цифры)' }, (price) => {
                    if (price && !isNaN(parseInt(price)) && parseInt(price) > 0) {
                        handleSetPrice(parseInt(price));
                    } else if (price) {
                        tg.showAlert('Пожалуйста, введите корректное число больше нуля.');
                    }
                    return true;
                });
                break;
        }
    }

    async function setPeriodAvailability(isAvailable, comment) {
        const dates = [];
        const endDate = selection.end || selection.start;
        for (let d = new Date(selection.start); d <= endDate; d.setUTCDate(d.getUTCDate() + 1)) {
            dates.push(d.toISOString().split('T')[0]);
        }
        
        setLoaderVisible(true);
        try {
            const response = await fetch(`/api/owner/set_availability`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    property_id: propertyId, 
                    dates, 
                    is_available: isAvailable,
                    comment
                })
            });
            if (!response.ok) throw new Error('Ошибка сервера.');
            tg.showPopup({ title: 'Успех', message: `Статус для выбранного периода успешно изменен.` });
        } catch (error) {
            tg.showAlert(`Ошибка: ${error.message}`);
        } finally {
            await reloadCalendar();
        }
    }

    async function handleSetPrice(price) {
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
                    price: price
                })
            });
            if (!response.ok) throw new Error('Ошибка сервера при установке цены.');
            tg.showPopup({ title: 'Успех', message: `Цена ${price}₽ установлена для периода с ${startDate} по ${endDate}.` });
        } catch (error) {
            tg.showAlert(`Ошибка: ${error.message}`);
        } finally {
            await reloadCalendar();
        }
    }

    async function reloadCalendar() {
        resetSelection();
        calendarContainer.innerHTML = '';
        calendarData = {};
        await main();
    }
    
    async function fetchAndRenderMonth(year, month) {
        if (isLoading) return;
        isLoading = true;
        setLoaderVisible(true);
        try {
            const fetchUrl = `/api/calendar_data/${propertyId}?year=${year}&month=${month + 1}`;
            const response = await fetch(fetchUrl);
            if (!response.ok) { throw new Error(`Ошибка сети: ${response.status}`); }
            const data = await response.json();
            data.forEach(dayInfo => { calendarData[dayInfo.date] = dayInfo; });
            renderMonth(year, month);
        } catch (error) {
            console.error('Ошибка при загрузке данных месяца:', error);
            tg.showAlert('Не удалось загрузить данные календаря. Попробуйте позже.');
        } finally {
            isLoading = false;
            setLoaderVisible(false);
        }
    }
    
    function renderMonth(year, month) {
        const monthContainerId = `month-${year}-${month}`;
        if (document.getElementById(monthContainerId)) return;
        const monthContainer = document.createElement('div');
        monthContainer.className = 'calendar-month-container';
        monthContainer.id = monthContainerId;
        const header = document.createElement('div');
        header.className = 'calendar-header';
        header.textContent = `${monthNames[month]} ${year}`;
        monthContainer.appendChild(header);
        const weekdaysGrid = document.createElement('div');
        weekdaysGrid.className = 'calendar-grid';
        dayNames.forEach(day => {
            const weekdayEl = document.createElement('div');
            weekdayEl.className = 'calendar-weekday';
            weekdayEl.textContent = day;
            weekdaysGrid.appendChild(weekdayEl);
        });
        monthContainer.appendChild(weekdaysGrid);
        
        const calendarGrid = document.createElement('div');
        calendarGrid.className = 'calendar-grid';
        const firstDayOfMonth = new Date(year, month, 1).getDay();
        const startingDay = (firstDayOfMonth === 0) ? 6 : firstDayOfMonth - 1;
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        for (let i = 0; i < startingDay; i++) {
            const emptyCell = document.createElement('div');
            emptyCell.className = 'day-cell empty';
            calendarGrid.appendChild(emptyCell);
        }
        for (let day = 1; day <= daysInMonth; day++) {
            const currentDate = new Date(Date.UTC(year, month, day));
            const currentDateStr = currentDate.toISOString().split('T')[0];
            const dayData = calendarData[currentDateStr] || { status: 'available', price: null };
            const dayEl = document.createElement('div');
            dayEl.className = 'day-cell';
            dayEl.dataset.date = currentDateStr;
            const dayNumber = document.createElement('div');
            dayNumber.className = 'day-number';
            dayNumber.textContent = day;
            dayEl.appendChild(dayNumber);
            const dayPrice = document.createElement('div');
            dayPrice.className = 'day-price';
            
            if (dayData.price) dayPrice.textContent = `${dayData.price}₽`;
            dayEl.appendChild(dayPrice);
            
            dayEl.classList.add(dayData.status);
            if (dayData.status === 'past' || dayData.status === 'booked') {
                dayEl.classList.add('disabled');
            }
            
            calendarGrid.appendChild(dayEl);
        }
        monthContainer.appendChild(calendarGrid);
        calendarContainer.appendChild(monthContainer);
        updateSelectionHighlight();
    }

    async function main() {
        let currentYear = new Date().getFullYear();
        let currentMonth = new Date().getMonth();
        const loadMonths = async () => {
            for (let i = 0; i < 3; i++) {
                let yearToLoad = currentYear;
                let monthToLoad = currentMonth + i;
                if (monthToLoad > 11) {
                    yearToLoad += Math.floor(monthToLoad / 12);
                    monthToLoad = monthToLoad % 12;
                }
                await fetchAndRenderMonth(yearToLoad, monthToLoad);
            }
        };

        await loadMonths();

        calendarWrapper.addEventListener('scroll', async () => {
            const isAtBottom = calendarWrapper.scrollHeight - calendarWrapper.scrollTop <= calendarWrapper.clientHeight + 1;
            if (isAtBottom && !isLoading) {
                currentMonth += 3;
                if (currentMonth > 11) {
                    currentMonth %= 12;
                    currentYear++;
                }
                await loadMonths();
            }
        });
    }

    main();
});