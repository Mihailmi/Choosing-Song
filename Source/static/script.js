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
            displayResults(data);
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
    const { candidates, selected, reasoning } = data;
    
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
        reasoningSection.style.display = 'block';
    } else {
        reasoningSection.style.display = 'none';
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
    const artist = song.artist || 'Неизвестный исполнитель';
    
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
    
    if (song.lyrics) {
        let lyrics = Array.isArray(song.lyrics) ? song.lyrics.join('\n') : song.lyrics;
        hasFullLyrics = lyrics.length > 150;
        
        if (hasFullLyrics) {
            lyricsPreview = `<div class="lyrics-preview">${escapeHtml(lyrics.substring(0, 150))}...</div>`;
            lyricsHTML = `<div class="lyrics-full" style="display: none;">${escapeHtml(lyrics)}</div>`;
        } else {
            lyricsPreview = `<div class="lyrics-preview">${escapeHtml(lyrics)}</div>`;
        }
    }
    
    const toggleButtonHTML = hasFullLyrics 
        ? `<button class="toggle-lyrics-btn" onclick="toggleLyrics(this)">📝 Показать полный текст</button>`
        : '';
    
    card.innerHTML = `
        <h3>${index}. ${escapeHtml(title)}</h3>
        <div class="artist">👤 ${escapeHtml(artist)}</div>
        ${themesHTML}
        ${moodHTML}
        ${lyricsPreview}
        ${lyricsHTML}
        ${toggleButtonHTML}
    `;
    
    return card;
}

// Функция переключения отображения полного текста
function toggleLyrics(button) {
    const card = button.closest('.candidate-card');
    const lyricsFull = card.querySelector('.lyrics-full');
    const lyricsPreview = card.querySelector('.lyrics-preview');
    
    if (lyricsFull && lyricsFull.style.display === 'none') {
        lyricsFull.style.display = 'block';
        lyricsPreview.style.display = 'none';
        button.textContent = '📝 Скрыть текст';
    } else {
        lyricsFull.style.display = 'none';
        lyricsPreview.style.display = 'block';
        button.textContent = '📝 Показать полный текст';
    }
}

// Создание HTML для выбранной песни
function createSelectedSongHTML(song) {
    const title = song.title || 'Без названия';
    const artist = song.artist || 'Неизвестный исполнитель';
    
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
    if (song.lyrics) {
        let lyrics = Array.isArray(song.lyrics) ? song.lyrics.join('\n') : song.lyrics;
        lyricsHTML = `<div class="lyrics">${escapeHtml(lyrics)}</div>`;
    }
    
    return `
        <h3>🎵 ${escapeHtml(title)}</h3>
        <div class="artist">👤 ${escapeHtml(artist)}</div>
        ${themesHTML}
        ${moodHTML}
        ${lyricsHTML}
    `;
}

// Утилиты
function setLoading(loading) {
    searchBtn.disabled = loading;
    queryInput.disabled = loading;
    
    const btnText = searchBtn.querySelector('.btn-text');
    const btnLoader = searchBtn.querySelector('.btn-loader');
    
    if (loading) {
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline';
    } else {
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
    }
}

function showStatus(message, type = 'info') {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
    statusMessage.style.display = 'block';
}

function hideStatus() {
    statusMessage.style.display = 'none';
}

function showResults() {
    resultsSection.style.display = 'block';
}

function hideResults() {
    resultsSection.style.display = 'none';
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
});

