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
            showStatus('Поиск выполнен успешно!', 'success');
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
    
    let lyricsPreview = '';
    if (song.lyrics) {
        let lyrics = Array.isArray(song.lyrics) ? song.lyrics.join('\n') : song.lyrics;
        if (lyrics.length > 150) {
            lyrics = lyrics.substring(0, 150) + '...';
        }
        lyricsPreview = `<div class="lyrics-preview">${escapeHtml(lyrics)}</div>`;
    }
    
    card.innerHTML = `
        <h3>${index}. ${escapeHtml(title)}</h3>
        <div class="artist">👤 ${escapeHtml(artist)}</div>
        ${themesHTML}
        ${moodHTML}
        ${lyricsPreview}
    `;
    
    return card;
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

