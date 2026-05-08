"""
Веб-приложение для поиска и выбора песен.
Flask веб-сервер с современным интерфейсом.
"""

import os
import sys
import json
import time
from collections import deque
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError, field_validator

# Добавляем путь к Source для импорта модулей
sys.path.insert(0, str(Path(__file__).parent))

from embeddings_manager import EmbeddingsManager
from song_search import SongSearch
from song_selector import SongSelector

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)

# Настройка Rate Limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"],
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://")
)

# Валидация входных данных
class SearchRequest(BaseModel):
    query: str
    use_hybrid: bool = True
    semantic_weight: float = 0.55
    keyword_weight: float = 0.45
    enhance_query: bool = True  # Предобработка запроса через AI для улучшения векторного поиска
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Запрос не может быть пустым')
        if len(v) > 500:
            raise ValueError('Запрос слишком длинный (максимум 500 символов)')
        return v.strip()
    
    @field_validator('semantic_weight', 'keyword_weight')
    @classmethod
    def validate_weights(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Веса должны быть от 0 до 1')
        return v

class FeedbackRequest(BaseModel):
    query: str
    selected_song_id: str
    feedback: str  # 'like' или 'dislike'
    
    @field_validator('feedback')
    @classmethod
    def validate_feedback(cls, v):
        if v not in ['like', 'dislike']:
            raise ValueError('Feedback должен быть "like" или "dislike"')
        return v

# Глобальные переменные для компонентов системы
embeddings_manager = None
search_engine = None
selector = None

# Хранилище feedback (в продакшене использовать БД)
feedback_storage = deque(maxlen=1000)


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
    selector = SongSelector(
        api_key=google_api_key,
        allow_blocking_retries=False
    )
    
    print("✅ Система инициализирована и готова к работе!")


@app.route('/')
def index():
    """Главная страница."""
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    """Обработчик для favicon."""
    from flask import send_from_directory
    return send_from_directory(app.static_folder, 'favicon.svg', mimetype='image/svg+xml')


@app.route('/api/search', methods=['POST'])
@limiter.limit("10 per minute")
def search_songs():
    """API endpoint для поиска песен."""
    try:
        # Валидация входных данных
        try:
            data = request.get_json() or {}
            search_request = SearchRequest(**data)
        except ValidationError as e:
            return jsonify({'error': 'Ошибка валидации', 'details': str(e)}), 400
        
        if search_engine is None or selector is None:
            return jsonify({'error': 'Система не инициализирована'}), 500
        
        # Предобработка запроса через AI для улучшения векторного поиска
        # Для векторного поиска используем: исходный запрос + уточнение от ИИ
        search_query = search_request.query
        enhanced_data = None
        
        if search_request.enhance_query:
            try:
                enhanced_data = selector.enhance_query(search_request.query)
                if enhanced_data and isinstance(enhanced_data, dict):
                    enhanced_query = enhanced_data.get("enhanced_query", "").strip()
                    
                    # Дополнительная валидация: проверяем, что enhanced_query валидный
                    if enhanced_query and enhanced_query != search_request.query:
                        # Проверяем, что это не служебный текст
                        if (len(enhanced_query) < 500 and 
                            "here is" not in enhanced_query.lower()[:100] and
                            "json" not in enhanced_query.lower()[:50] and
                            "```" not in enhanced_query):
                            # Комбинируем исходный запрос + уточнение от ИИ
                            search_query = f"{search_request.query} {enhanced_query}"
                            print(f"✨ Запрос для поиска:\n  Исходный: {search_request.query}\n  Уточнение: {enhanced_query}\n  Комбинированный: {search_query}")
                        else:
                            print(f"⚠️ Улучшенный запрос содержит служебный текст, используем исходный запрос")
                            search_query = search_request.query
                else:
                    # Обратная совместимость со старым форматом (строка)
                    if isinstance(enhanced_data, str) and enhanced_data != search_request.query:
                        search_query = f"{search_request.query} {enhanced_data}"
                        print(f"✨ Запрос для поиска:\n  Исходный: {search_request.query}\n  Уточнение: {enhanced_data}\n  Комбинированный: {search_query}")
            except Exception as e:
                print(f"⚠️ Ошибка при улучшении запроса, используем исходный: {e}")
                search_query = search_request.query
        
        # Поиск кандидатов (hybrid или обычный) с улучшенным запросом
        # k=12 — больше кандидатов, чтобы тематические песни (напр. про осень) попадали в выбор
        k_candidates = 12
        if search_request.use_hybrid and hasattr(search_engine, 'hybrid_search'):
            candidates = search_engine.hybrid_search(
                search_query, 
                k=k_candidates,
                semantic_weight=search_request.semantic_weight,
                keyword_weight=search_request.keyword_weight
            )
        else:
            candidates = search_engine.search(search_query, k=k_candidates)
        
        # Отладка: выводим структуру данных кандидатов
        print(f"\n🔍 Найдено {len(candidates)} кандидатов:")
        for idx, candidate in enumerate(candidates, 1):
            print(f"  {idx}. {candidate.get('title', 'Без названия')}")
            print(f"     Поля: {list(candidate.keys())}")
            print(f"     Есть lyrics? {bool(candidate.get('lyrics'))}")
            if candidate.get('lyrics'):
                lyrics = candidate.get('lyrics')
                print(f"     Тип lyrics: {type(lyrics)}, длина: {len(str(lyrics)) if lyrics else 0}")
        
        if not candidates:
            return jsonify({
                'candidates': [],
                'selected': None,
                'reasoning': None,
                'message': 'Не найдено подходящих песен'
            })
        
        # Выбор лучшей песни через LLM (используем ТОЛЬКО исходный запрос пользователя)
        try:
            result = selector.choose_best(search_request.query, candidates)
        except Exception as e:
            error_msg = str(e)
            # Если все модели перегружены или недоступны, возвращаем кандидатов без выбранной песни
            if ("недоступны" in error_msg or 
                "overloaded" in error_msg.lower() or 
                "перегружены" in error_msg.lower() or
                "Все модели" in error_msg):
                print(f"⚠️ Все модели недоступны/перегружены, возвращаем кандидатов без выбора: {e}")
                return jsonify({
                    'candidates': candidates,
                    'selected': None,
                    'reasoning': None,
                    'message': 'Модели временно недоступны. Показаны найденные кандидаты, но выбор лучшей песни недоступен. Попробуйте позже.',
                    'warning': True
                })
            elif "квота" in error_msg.lower() or "quota" in error_msg.lower():
                # Превышена квота API
                print(f"⚠️ Превышена квота API, возвращаем кандидатов без выбора: {e}")
                return jsonify({
                    'candidates': candidates,
                    'selected': None,
                    'reasoning': None,
                    'message': 'Превышена квота API. Показаны найденные кандидаты, но выбор лучшей песни недоступен. Попробуйте позже.',
                    'warning': True
                })
            else:
                # Другие ошибки пробрасываем
                raise
        
        # Форматирование ответа
        enhanced_query_value = None
        if search_request.enhance_query and enhanced_data:
            if isinstance(enhanced_data, dict):
                enhanced_query_value = enhanced_data.get("enhanced_query")
            elif isinstance(enhanced_data, str):
                enhanced_query_value = enhanced_data
        
        response = {
            'candidates': candidates,
            'selected': result['song'],
            'reasoning': result.get('reasoning'),
            'confidence': result.get('confidence', 0.5),
            'message': 'Поиск выполнен успешно',
            'enhanced_query': enhanced_query_value
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


@app.route('/api/feedback', methods=['POST'])
@limiter.limit("20 per minute")
def submit_feedback():
    """API endpoint для отправки feedback (лайки/дизлайки)."""
    try:
        # Валидация входных данных
        try:
            data = request.get_json() or {}
            feedback_request = FeedbackRequest(**data)
        except ValidationError as e:
            return jsonify({'error': 'Ошибка валидации', 'details': str(e)}), 400
        
        # Сохраняем feedback (в продакшене использовать БД)
        feedback_entry = {
            'query': feedback_request.query,
            'selected_song_id': feedback_request.selected_song_id,
            'feedback': feedback_request.feedback,
            'timestamp': time.time()
        }
        feedback_storage.append(feedback_entry)
        
        return jsonify({
            'status': 'success',
            'message': 'Feedback сохранён'
        })
        
    except Exception as e:
        print(f"Ошибка при сохранении feedback: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/feedback/stats', methods=['GET'])
def get_feedback_stats():
    """Получить статистику feedback."""
    try:
        likes = sum(1 for f in feedback_storage if f['feedback'] == 'like')
        dislikes = sum(1 for f in feedback_storage if f['feedback'] == 'dislike')
        
        return jsonify({
            'total': len(feedback_storage),
            'likes': likes,
            'dislikes': dislikes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Инициализация системы при импорте модуля (для работы с gunicorn)
# Это выполнится при запуске через gunicorn, но не при тестах
if os.getenv('SKIP_INIT') != 'true':
    try:
        if search_engine is None or selector is None:
            init_system()
    except Exception as e:
        print(f"⚠️ Предупреждение: Не удалось инициализировать систему при импорте: {e}")
        print("Система будет инициализирована при первом запросе или при запуске через __main__")


if __name__ == '__main__':
    try:
        print("🚀 Запуск веб-приложения...")
        if search_engine is None or selector is None:
            init_system()
        # Используем переменную окружения PORT для совместимости с облачными платформами
        port = int(os.getenv('PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        print(f"🌐 Сервер запущен на http://0.0.0.0:{port}")
        app.run(debug=debug, host='0.0.0.0', port=port)
    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")
        sys.exit(1)

