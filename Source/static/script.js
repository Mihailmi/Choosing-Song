// Элементы DOM
const searchForm = document.getElementById('searchForm');
const queryInput = document.getElementById('queryInput');
const searchBtn = document.getElementById('searchBtn');
const statusMessage = document.getElementById('statusMessage');
const resultsSection = document.getElementById('resultsSection');
const candidatesList = document.getElementById('candidatesList');
const selectedSong = document.getElementById('selectedSong');
const reasoningSection = document.getElementById('reasoningSection');
const reasoningText = document.getElementById('reasoningText');
const historySidebar = document.getElementById('historySidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');
const historyMenuBtn = document.getElementById('historyMenuBtn');
const closeHistoryBtn = document.getElementById('closeHistoryBtn');
const historyList = document.getElementById('historyList');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');

// Базовый URL приложения с песнями (открытие в новой вкладке)
const LYRICS_APP_BASE_URL = 'https://lyrics-app.onrender.com';

// Элементы модального окна подтверждения
// Элементы модального окна подтверждения
const confirmModal = document.getElementById('confirmModal');
const confirmModalOverlay = document.getElementById('confirmModalOverlay');
const confirmModalTitle = document.getElementById('confirmModalTitle');
const confirmModalMessage = document.getElementById('confirmModalMessage');
const confirmModalCancel = document.getElementById('confirmModalCancel');
const confirmModalConfirm = document.getElementById('confirmModalConfirm');

let currentSearchResult = null;

// Обработчик отправки формы
searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const query = queryInput.value.trim();
    if (!query) {
        showStatus('Запрос не может быть пустым', 'error');
        return;
    }
    
    await searchSongs(query);
});

// Обработчики для истории поиска
if (historyMenuBtn) {
    historyMenuBtn.addEventListener('click', () => {
        openHistorySidebar();
    });
}

if (closeHistoryBtn) {
    closeHistoryBtn.addEventListener('click', () => {
        closeHistorySidebar();
    });
}

if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', () => {
        closeHistorySidebar();
    });
}

if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener('click', () => {
        showConfirmModal(
            'Очистить историю поиска?',
            'Вы уверены, что хотите очистить всю историю поиска? Это действие нельзя отменить.',
            () => {
                localStorage.removeItem('searchHistory');
                updateSearchHistory();
                closeConfirmModal();
            }
        );
    });
}

// Функции для работы с модальным окном подтверждения
let confirmCallback = null;

function showConfirmModal(title, message, onConfirm) {
    if (confirmModalTitle) confirmModalTitle.textContent = title;
    if (confirmModalMessage) confirmModalMessage.textContent = message;
    confirmCallback = onConfirm;
    
    if (confirmModal) confirmModal.classList.add('active');
    if (confirmModalOverlay) confirmModalOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeConfirmModal() {
    if (confirmModal) confirmModal.classList.remove('active');
    if (confirmModalOverlay) confirmModalOverlay.classList.remove('active');
    document.body.style.overflow = '';
    confirmCallback = null;
}

// Обработчики для модального окна подтверждения
if (confirmModalCancel) {
    confirmModalCancel.addEventListener('click', () => {
        closeConfirmModal();
    });
}

if (confirmModalOverlay) {
    confirmModalOverlay.addEventListener('click', () => {
        closeConfirmModal();
    });
}

if (confirmModalConfirm) {
    confirmModalConfirm.addEventListener('click', () => {
        if (confirmCallback) {
            confirmCallback();
        }
        closeConfirmModal();
    });
}

// Функции для открытия/закрытия бокового меню
function openHistorySidebar() {
    if (historySidebar) {
        historySidebar.classList.add('active');
    }
    if (sidebarOverlay) {
        sidebarOverlay.classList.add('active');
    }
    document.body.style.overflow = 'hidden'; // Блокируем прокрутку фона
}

function closeHistorySidebar() {
    if (historySidebar) {
        historySidebar.classList.remove('active');
    }
    if (sidebarOverlay) {
        sidebarOverlay.classList.remove('active');
    }
    document.body.style.overflow = ''; // Разблокируем прокрутку
}

// Функция поиска песен
async function searchSongs(query) {
    // Показываем загрузку
    setLoading(true);
    hideStatus();
    hideResults();
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Ошибка при поиске');
        }
        
        if (data.candidates && data.candidates.length > 0) {
            // Отладка: выводим данные, полученные с сервера
            console.log('📥 Данные получены с сервера:', data);
            console.log('📋 Кандидаты:', data.candidates);
            data.candidates.forEach((candidate, idx) => {
                console.log(`Кандидат ${idx + 1}:`, {
                    title: candidate.title,
                    keys: Object.keys(candidate),
                    hasLyrics: !!candidate.lyrics,
                    lyricsType: candidate.lyrics ? typeof candidate.lyrics : 'нет',
                    lyricsValue: candidate.lyrics ? (Array.isArray(candidate.lyrics) ? `массив[${candidate.lyrics.length}]` : String(candidate.lyrics).substring(0, 100)) : 'нет'
                });
            });
            
            displayResults(data);
            
            // Сохраняем в историю
            saveSearchHistory(query, data);
            updateSearchHistory();
            
            currentSearchResult = { query, selected: data.selected };
            
            // Показываем предупреждение, если модели перегружены
            if (data.warning) {
                showStatus(data.message || 'Модели временно перегружены', 'warning');
            } else {
                showStatus('Поиск выполнен успешно!', 'success');
            }
        } else {
            showStatus(data.message || 'Не найдено подходящих песен', 'info');
        }
        
    } catch (error) {
        console.error('Ошибка:', error);
        showStatus(`Ошибка: ${error.message}`, 'error');
    } finally {
        setLoading(false);
    }
}

// Отображение результатов
function displayResults(data) {
    const { candidates, selected, reasoning, enhanced_query } = data;
    
    // Отображаем улучшенный запрос, если он был создан
    if (enhanced_query) {
        console.log('✨ Запрос был улучшен:', enhanced_query);
        // Можно добавить визуальное отображение улучшенного запроса
    }
    
    // Отображаем кандидатов
    candidatesList.innerHTML = '';
    candidates.forEach((candidate, index) => {
        const card = createCandidateCard(candidate, index + 1, selected);
        candidatesList.appendChild(card);
    });
    
    // Отображаем выбранную песню
    if (selected) {
        selectedSong.innerHTML = createSelectedSongHTML(selected);
    } else {
        // Если песня не выбрана (модели перегружены), показываем сообщение
        selectedSong.innerHTML = `
            <div style="text-align: center; padding: 20px; color: var(--text-secondary);">
                <p style="font-size: 1.1rem; margin-bottom: 10px;">⚠️ Автоматический выбор недоступен</p>
                <p style="font-size: 0.95rem;">Модели временно перегружены. Пожалуйста, выберите песню из списка кандидатов вручную.</p>
            </div>
        `;
    }
    
    // Отображаем объяснение
    if (reasoning) {
        reasoningText.textContent = reasoning;
        reasoningSection.classList.remove('hidden');
    } else {
        reasoningSection.classList.add('hidden');
    }
    
    showResults();
}

// Создание карточки кандидата
function createCandidateCard(song, index, selectedSong) {
    const card = document.createElement('div');
    card.className = 'candidate-card';
    
    if (selectedSong && song.id === selectedSong.id) {
        card.classList.add('selected');
    }
    
    const title = song.title || 'Без названия';
    
    // Номер песни из сборника
    let numberText = '';
    if (song.number !== undefined) {
        numberText = `№${song.number}`;
    }
    
    // Отладка: выводим структуру данных песни
    console.log(`Песня ${index}:`, song);
    console.log(`Есть lyrics?`, !!song.lyrics, song.lyrics ? typeof song.lyrics : 'нет');
    
    let themesHTML = '';
    if (song.themes) {
        const themes = Array.isArray(song.themes) ? song.themes : [song.themes];
        themesHTML = `<div class="themes">${themes.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}</div>`;
    }
    
    let moodHTML = '';
    if (song.mood) {
        const moods = Array.isArray(song.mood) ? song.mood : [song.mood];
        moodHTML = `<div class="mood">${moods.map(m => `<span class="tag">${escapeHtml(m)}</span>`).join('')}</div>`;
    }
    
    let lyricsHTML = '';
    let lyricsPreview = '';
    let hasFullLyrics = false;
    let hasLyrics = false;
    
    // Проверяем наличие текста в разных возможных полях
    let lyrics = song.lyrics || song.text || song.content || null;
    
    if (lyrics) {
        hasLyrics = true;
        // Обрабатываем lyrics - может быть строкой, массивом строк или объектом
        if (Array.isArray(lyrics)) {
            lyrics = lyrics.join('\n');
        } else if (typeof lyrics === 'object') {
            // Если это объект, пытаемся извлечь текст
            lyrics = JSON.stringify(lyrics);
        }
        
        // Убеждаемся, что это строка
        lyrics = String(lyrics).trim();
        hasFullLyrics = lyrics.length > 150;
        
        if (hasFullLyrics) {
            lyricsPreview = `<div class="lyrics-preview">${escapeHtml(lyrics.substring(0, 150))}...</div>`;
            lyricsHTML = `<div class="lyrics-full" style="display: none;">${escapeHtml(lyrics)}</div>`;
        } else {
            // Для коротких текстов тоже делаем возможность скрыть/показать
            lyricsPreview = `<div class="lyrics-preview">${escapeHtml(lyrics)}</div>`;
            lyricsHTML = `<div class="lyrics-full" style="display: none;">${escapeHtml(lyrics)}</div>`;
        }
    } else {
        console.log(`⚠️ У песни ${index} нет текста! Доступные поля:`, Object.keys(song));
        // Показываем сообщение, что текста нет
        lyricsPreview = `<div class="lyrics-preview" style="color: var(--text-muted); font-style: italic;">Текст песни недоступен</div>`;
    }
    
    // Строка действий: слева — «Показать текст», справа — иконка «Открыть в приложении»
    const toggleButtonHTML = hasLyrics 
        ? `<button class="toggle-lyrics-btn" onclick="toggleLyrics(this)">${hasFullLyrics ? '📝 Показать полный текст' : '📝 Показать текст'}</button>`
        : '';
    const openInAppHTML = song.id
        ? `<a href="${LYRICS_APP_BASE_URL}/songs/view/${encodeURIComponent(song.id)}" target="_blank" rel="noopener noreferrer" class="open-in-app-btn icon-only" title="Открыть в приложении" aria-label="Открыть в приложении">🔗</a>`
        : '';
    const cardActionsHTML = (toggleButtonHTML || openInAppHTML)
        ? `<div class="card-actions-row">${toggleButtonHTML}${openInAppHTML}</div>`
        : '';
    
    // Визуализация соответствия: приоритет у относительного процента (лучший = 100%), затем гибрид, затем L2
    let similarityHTML = '';
    if (song.match_percent !== undefined) {
        const similarity = Math.max(0, Math.min(100, song.match_percent));
        similarityHTML = `
            <div class="similarity-container">
                <div class="similarity-label">Соответствие: ${similarity.toFixed(1)}%</div>
                <div class="similarity-bar-container">
                    <div class="similarity-bar" style="width: ${similarity}%"></div>
                </div>
            </div>
        `;
    } else if (song.hybrid_score !== undefined) {
        const similarity = Math.max(0, Math.min(100, song.hybrid_score * 100));
        similarityHTML = `
            <div class="similarity-container">
                <div class="similarity-label">Соответствие: ${similarity.toFixed(1)}%</div>
                <div class="similarity-bar-container">
                    <div class="similarity-bar" style="width: ${similarity}%"></div>
                </div>
            </div>
        `;
    } else if (song.similarity_distance !== undefined) {
        const similarity = Math.max(0, Math.min(100, (1 - Math.min(song.similarity_distance, 2) / 2) * 100));
        similarityHTML = `
            <div class="similarity-container">
                <div class="similarity-label">Соответствие: ${similarity.toFixed(1)}%</div>
                <div class="similarity-bar-container">
                    <div class="similarity-bar" style="width: ${similarity}%"></div>
                </div>
            </div>
        `;
    }
    
    card.innerHTML = `
        <h3>${index}. ${escapeHtml(title)}${numberText ? ` <span class="song-number-inline">(${numberText})</span>` : ''}</h3>
        ${similarityHTML}
        ${themesHTML}
        ${moodHTML}
        ${lyricsPreview}
        ${lyricsHTML}
        ${cardActionsHTML}
    `;
    
    // Добавляем обработчик клика на карточку (кроме кнопки и ссылки в приложение)
    if (hasLyrics) {
        card.addEventListener('click', (e) => {
            if (e.target.classList.contains('toggle-lyrics-btn') || e.target.closest('.toggle-lyrics-btn') ||
                e.target.classList.contains('open-in-app-btn') || e.target.closest('.open-in-app-btn')) {
                return;
            }
            // Ищем кнопку в карточке и вызываем её клик
            const button = card.querySelector('.toggle-lyrics-btn');
            if (button) {
                toggleLyrics(button);
            }
        });
    }
    
    return card;
}

// Функция переключения отображения полного текста
function toggleLyrics(button) {
    const card = button.closest('.candidate-card');
    if (!card) {
        console.error('Не найдена карточка для кнопки');
        return;
    }
    
    const lyricsFull = card.querySelector('.lyrics-full');
    const lyricsPreview = card.querySelector('.lyrics-preview');
    
    if (!lyricsFull || !lyricsPreview) {
        console.error('Не найдены элементы текста в карточке', { lyricsFull, lyricsPreview });
        return;
    }
    
    const isCurrentlyHidden = lyricsFull.style.display === 'none' || lyricsFull.style.display === '';
    
    if (isCurrentlyHidden) {
        lyricsFull.style.display = 'block';
        lyricsPreview.style.display = 'none';
        button.textContent = '📝 Скрыть текст';
        // Прокручиваем к тексту для удобства
        lyricsFull.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
        lyricsFull.style.display = 'none';
        lyricsPreview.style.display = 'block';
        const previewText = lyricsPreview.textContent || '';
        const isLong = previewText.length > 150 || previewText.includes('...');
        button.textContent = isLong ? '📝 Показать полный текст' : '📝 Показать текст';
    }
}

// Создание HTML для выбранной песни
function createSelectedSongHTML(song) {
    const title = song.title || 'Без названия';
    
    // Номер песни из сборника
    let numberText = '';
    if (song.number !== undefined) {
        numberText = `№${song.number}`;
    }
    
    let themesHTML = '';
    if (song.themes) {
        const themes = Array.isArray(song.themes) ? song.themes : [song.themes];
        themesHTML = `<div class="themes">${themes.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}</div>`;
    }
    
    let moodHTML = '';
    if (song.mood) {
        const moods = Array.isArray(song.mood) ? song.mood : [song.mood];
        moodHTML = `<div class="mood">${moods.map(m => `<span class="tag">${escapeHtml(m)}</span>`).join('')}</div>`;
    }
    
    let lyricsHTML = '';
    // Проверяем наличие текста в разных возможных полях
    let lyrics = song.lyrics || song.text || song.content || null;
    if (lyrics) {
        // Обрабатываем lyrics - может быть строкой, массивом строк или объектом
        if (Array.isArray(lyrics)) {
            lyrics = lyrics.join('\n');
        } else if (typeof lyrics === 'object') {
            // Если это объект, пытаемся извлечь текст
            lyrics = JSON.stringify(lyrics);
        }
        // Убеждаемся, что это строка
        lyrics = String(lyrics).trim();
        if (lyrics) {
            lyricsHTML = `<div class="lyrics">${escapeHtml(lyrics)}</div>`;
        }
    }
    
    const openInAppHTML = song.id
        ? `<a href="${LYRICS_APP_BASE_URL}/songs/view/${encodeURIComponent(song.id)}" target="_blank" rel="noopener noreferrer" class="open-in-app-btn icon-only" title="Открыть в приложении" aria-label="Открыть в приложении">🔗</a>`
        : '';
    
    return `
        <h3>🎵 ${escapeHtml(title)}${numberText ? ` <span class="song-number-inline">(${numberText})</span>` : ''}</h3>
        ${themesHTML}
        ${moodHTML}
        ${lyricsHTML}
        ${openInAppHTML}
    `;
}

// Утилиты
function setLoading(loading) {
    searchBtn.disabled = loading;
    queryInput.disabled = loading;
    
    const btnText = searchBtn.querySelector('.btn-text');
    const btnLoader = searchBtn.querySelector('.btn-loader');
    
    if (loading) {
        btnText.classList.add('hide');
        btnLoader.classList.add('show');
    } else {
        btnText.classList.remove('hide');
        btnLoader.classList.remove('show');
    }
}

function showStatus(message, type = 'info') {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    statusMessage.classList.remove('hidden');
}

function hideStatus() {
    statusMessage.classList.add('hidden');
}

function showResults() {
    resultsSection.classList.remove('hidden');
}

function hideResults() {
    resultsSection.classList.add('hidden');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Упрощённый рендер Markdown для объяснения (жирный + переносы строк)
function formatReasoning(text) {
    if (!text) return '';
    // Экранируем HTML, затем подсвечиваем **жирный** и переносы строк
    const escaped = escapeHtml(text);
    const bolded = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    return bolded
        .replace(/\n\n+/g, '<br><br>')
        .replace(/\n/g, '<br>');
}

// История поиска
function saveSearchHistory(query, result) {
    const history = JSON.parse(localStorage.getItem('searchHistory') || '[]');
    history.unshift({
        query: query,
        timestamp: Date.now(),
        selectedTitle: result.selected?.title || null,
        // Сохраняем полные результаты для кэширования
        cachedResult: result
    });
    // Храним только последние 10 записей
    const limitedHistory = history.slice(0, 10);
    localStorage.setItem('searchHistory', JSON.stringify(limitedHistory));
}

function updateSearchHistory() {
    const history = JSON.parse(localStorage.getItem('searchHistory') || '[]');
    
    // Показываем всю историю полностью
    if (historyList) {
        historyList.innerHTML = '';
        if (history.length > 0) {
            history.forEach((item) => {
                const historyItem = createHistoryItem(item);
                historyList.appendChild(historyItem);
            });
        } else {
            historyList.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 20px;">История поиска пуста</p>';
        }
    }
}

function createHistoryItem(item) {
    const historyItem = document.createElement('div');
    historyItem.className = 'history-item';
    const date = new Date(item.timestamp);
    // Форматируем дату и время отдельно
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const dateStr = `${day}.${month}.${year}`;
    const timeStr = `${hours}:${minutes}`;
    historyItem.innerHTML = `
        <span class="history-query">${escapeHtml(item.query)}</span>
        <div class="history-datetime">
            <span class="history-date">${dateStr}</span>
            <span class="history-time">${timeStr}</span>
        </div>
        <button class="history-use-btn" onclick="useHistoryQuery('${escapeHtml(item.query)}')" title="Использовать">→</button>
    `;
    return historyItem;
}

function useHistoryQuery(query) {
    queryInput.value = query;
    
    // Закрываем боковое меню
    closeHistorySidebar();
    
    // Проверяем, есть ли кэшированные результаты для этого запроса
    const history = JSON.parse(localStorage.getItem('searchHistory') || '[]');
    const cachedEntry = history.find(item => item.query === query && item.cachedResult);
    
    if (cachedEntry && cachedEntry.cachedResult) {
        // Используем кэшированные результаты
        console.log('📦 Используем кэшированные результаты для:', query);
        displayResults(cachedEntry.cachedResult);
        showStatus('Результаты загружены из кэша', 'success');
        showResults();
        
        currentSearchResult = { query, selected: cachedEntry.cachedResult.selected };
    } else {
        // Если кэша нет, делаем новый запрос
        console.log('🔄 Кэш не найден, делаем новый запрос для:', query);
        searchSongs(query);
    }
}

// Проверка состояния системы при загрузке
window.addEventListener('load', async () => {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        
        if (data.status === 'ok') {
            console.log('Система готова к работе');
        } else {
            showStatus('Система не готова к работе', 'error');
        }
    } catch (error) {
        console.error('Ошибка проверки состояния:', error);
    }
    
    // Загружаем историю поиска
    updateSearchHistory();
});

