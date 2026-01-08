"""
Пример использования RAG системы для выбора песен.
Демонстрирует программное использование без интерактивного режима.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Добавляем путь к Source для импорта модулей
sys.path.insert(0, str(Path(__file__).parent))

from embeddings_manager import EmbeddingsManager
from song_search import SongSearch
from song_selector import SongSelector

# Загрузка переменных окружения
load_dotenv()


def example_search():
    """Пример поиска и выбора песни."""
    
    # Пути к файлам
    project_root = Path(__file__).parent.parent
    index_path = project_root / "Data" / "songs_index.faiss"
    metadata_path = project_root / "Data" / "songs_metadata.json"
    
    # Проверка наличия индекса
    if not index_path.exists() or not metadata_path.exists():
        print("❌ Индекс не найден!")
        print("Сначала запустите prepare_embeddings.py")
        return
    
    # Инициализация
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY не установлен!")
        return
    
    print("🔧 Инициализация системы...")
    embeddings_manager = EmbeddingsManager(api_key=api_key)
    embeddings_manager.load_index(str(index_path), str(metadata_path))
    
    search_engine = SongSearch(embeddings_manager)
    selector = SongSelector(api_key=api_key)
    
    # Примеры запросов
    queries = [
        "Хочу что-то спокойное и задумчивое",
        "Нужна песня про любовь",
        "Ищу что-то энергичное и мотивирующее"
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"🔍 Запрос: '{query}'")
        print('='*60)
        
        # Поиск кандидатов
        candidates = search_engine.search(query, k=5)
        print(f"\n✅ Найдено {len(candidates)} кандидатов:")
        for idx, song in enumerate(candidates, 1):
            title = song.get("title", "Без названия")
            artist = song.get("artist", "Неизвестный")
            print(f"  {idx}. {title} - {artist}")
        
        # Выбор лучшей
        print("\n🧠 Выбираю лучшую песню...")
        try:
            result = selector.choose_best(query, candidates)
            # Результат
            print(f"\n⭐ ВЫБРАННАЯ ПЕСНЯ:")
            print(f"   {result['song'].get('title')} - {result['song'].get('artist')}")
            if result.get('reasoning'):
                print(f"\n💭 Объяснение:\n{result['reasoning']}")
        except Exception as e:
            # Если LLM не работает, возвращаем топ результат
            print(f"⚠️  LLM выбор недоступен: {e}")
            print(f"\n⭐ РЕКОМЕНДУЕМАЯ ПЕСНЯ (топ результат поиска):")
            top_song = candidates[0]
            print(f"   {top_song.get('title')} - {top_song.get('artist')}")
            print(f"\n💡 Это наиболее релевантная песня по семантическому поиску.")


if __name__ == "__main__":
    example_search()

