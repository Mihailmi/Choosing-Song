"""
Веб-приложение для поиска и выбора песен.
Flask веб-сервер с современным интерфейсом.
"""

import os
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Добавляем путь к Source для импорта модулей
sys.path.insert(0, str(Path(__file__).parent))

from embeddings_manager import EmbeddingsManager
from song_search import SongSearch
from song_selector import SongSelector

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)

# Глобальные переменные для компонентов системы
embeddings_manager = None
search_engine = None
selector = None


def init_system():
    """Инициализирует систему поиска песен."""
    global embeddings_manager, search_engine, selector
    
    # Пути к файлам
    project_root = Path(__file__).parent.parent
    index_path = project_root / "Data" / "songs_index.faiss"
    metadata_path = project_root / "Data" / "songs_metadata.json"
    
    # Проверка наличия индекса
    if not index_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(
            "Индекс не найден! Сначала запустите prepare_embeddings.py для создания индекса."
        )
    
    # Проверка API ключа
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError(
            "GOOGLE_API_KEY не установлен! Создайте файл .env и добавьте: GOOGLE_API_KEY=your_key_here"
        )
    
    # Инициализация компонентов
    embeddings_manager = EmbeddingsManager(api_key=google_api_key)
    embeddings_manager.load_index(str(index_path), str(metadata_path))
    
    search_engine = SongSearch(embeddings_manager)
    selector = SongSelector(api_key=google_api_key)
    
    print("✅ Система инициализирована и готова к работе!")


@app.route('/')
def index():
    """Главная страница."""
    return render_template('index.html')


@app.route('/api/search', methods=['POST'])
def search_songs():
    """API endpoint для поиска песен."""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'error': 'Запрос не может быть пустым'}), 400
        
        if search_engine is None or selector is None:
            return jsonify({'error': 'Система не инициализирована'}), 500
        
        # Поиск кандидатов
        candidates = search_engine.search(query, k=5)
        
        if not candidates:
            return jsonify({
                'candidates': [],
                'selected': None,
                'reasoning': None,
                'message': 'Не найдено подходящих песен'
            })
        
        # Выбор лучшей песни через LLM
        result = selector.choose_best(query, candidates)
        
        # Форматирование ответа
        response = {
            'candidates': candidates,
            'selected': result['song'],
            'reasoning': result.get('reasoning'),
            'message': 'Поиск выполнен успешно'
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Ошибка при поиске: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка состояния системы."""
    try:
        if search_engine is None or selector is None:
            return jsonify({
                'status': 'error',
                'message': 'Система не инициализирована'
            }), 500
        
        return jsonify({
            'status': 'ok',
            'message': 'Система готова к работе'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# Инициализация системы при импорте модуля (для работы с gunicorn)
# Это выполнится при запуске через gunicorn, но не при тестах
if os.getenv('SKIP_INIT') != 'true':
    try:
        init_system()
    except Exception as e:
        print(f"⚠️ Предупреждение: Не удалось инициализировать систему при импорте: {e}")
        print("Система будет инициализирована при первом запросе или при запуске через __main__")


if __name__ == '__main__':
    try:
        print("🚀 Запуск веб-приложения...")
        init_system()
        # Используем переменную окружения PORT для совместимости с облачными платформами
        port = int(os.getenv('PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        print(f"🌐 Сервер запущен на http://0.0.0.0:{port}")
        app.run(debug=debug, host='0.0.0.0', port=port)
    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")
        sys.exit(1)

