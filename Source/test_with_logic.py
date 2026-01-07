"""
Тест использования существующей логики с рабочим Google API.
Демонстрирует работу EmbeddingsManager и поиск песен.
"""

import os
import sys
import json
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

# Добавляем путь к Source для импорта модулей
source_dir = Path(__file__).parent
sys.path.insert(0, str(source_dir))

# Импорт EmbeddingsManager
from embeddings_manager import EmbeddingsManager

# Загрузка переменных окружения
load_dotenv()


def test_with_existing_logic():
    """Тест с использованием существующей логики проекта."""
    
    print("=" * 60)
    print("🎵 Тест системы поиска песен с существующей логикой")
    print("=" * 60)
    
    # Проверка API ключа
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY не найден!")
        print("   Создайте файл .env с: GOOGLE_API_KEY=your_key")
        return
    
    # Пути к файлам
    project_root = Path(__file__).parent.parent
    songs_path = project_root / "Data" / "Songs.json"
    
    if not songs_path.exists():
        print(f"❌ Файл не найден: {songs_path}")
        return
    
    print(f"\n📖 Загрузка песен из {songs_path}...")
    
    # Загрузка песен
    try:
        with open(songs_path, 'r', encoding='utf-8') as f:
            songs_data = json.load(f)
        
        # Обработка разных форматов JSON
        if isinstance(songs_data, dict):
            if "songs" in songs_data:
                songs = songs_data["songs"]
            elif "data" in songs_data:
                songs = songs_data["data"]
            else:
                for key, value in songs_data.items():
                    if isinstance(value, list):
                        songs = value
                        break
        else:
            songs = songs_data
        
        if not isinstance(songs, list):
            print("❌ Не удалось найти список песен")
            return
        
        print(f"✅ Загружено {len(songs)} песен")
        
        # Берём первые 5 песен для быстрого теста
        test_songs = songs[:5]
        print(f"\n🎯 Используем {len(test_songs)} песен для теста")
        for idx, song in enumerate(test_songs, 1):
            title = song.get("title", "Без названия")
            print(f"   {idx}. {title}")
        
    except Exception as e:
        print(f"❌ Ошибка при загрузке: {e}")
        return
    
    # Инициализация EmbeddingsManager с рабочим Google API
    print("\n🔧 Инициализация EmbeddingsManager...")
    try:
        embeddings_manager = EmbeddingsManager(api_key=api_key)
        print("✅ EmbeddingsManager создан")
    except Exception as e:
        print(f"❌ Ошибка создания EmbeddingsManager: {e}")
        return
    
    # Создание embeddings для тестовых песен
    print("\n🧠 Создание embeddings для песен...")
    try:
        vectors = embeddings_manager.create_embeddings(test_songs)
        
        if not vectors:
            print("❌ Не удалось создать embeddings")
            return
        
        print(f"✅ Создано {len(vectors)} embeddings")
        
    except Exception as e:
        print(f"❌ Ошибка при создании embeddings: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Построение индекса
    print("\n📊 Построение FAISS индекса...")
    try:
        embeddings_manager.build_index(vectors)
        print("✅ Индекс построен")
    except Exception as e:
        print(f"❌ Ошибка при построении индекса: {e}")
        return
    
    # Функция поиска (упрощённая версия SongSearch)
    def search_songs(query: str, k: int = 5):
        """Поиск песен по запросу."""
        # Создание embedding для запроса
        query_embedding = embeddings_manager.get_query_embedding(query)
        
        # Поиск в индексе
        distances, indices = embeddings_manager.index.search(query_embedding, k)
        
        # Получение метаданных найденных песен
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(embeddings_manager.vectors_metadata):
                song_data = embeddings_manager.vectors_metadata[idx]["metadata"].copy()
                song_data["similarity_distance"] = float(distance)
                results.append(song_data)
        
        return results
    
    print("\n🔍 Поисковая система готова")
    
    # Тестовые запросы
    test_queries = [
        "спокойная песня",
        "любовь",
        "энергичная музыка"
    ]
    
    print("\n" + "=" * 60)
    print("🔍 Тестирование поиска песен")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n📝 Запрос: '{query}'")
        print("-" * 60)
        
        try:
            # Поиск
            results = search_songs(query, k=3)
            
            if results:
                print(f"✅ Найдено {len(results)} песен:")
                for idx, song in enumerate(results, 1):
                    title = song.get("title", "Без названия")
                    artist = song.get("artist", "Неизвестный")
                    distance = song.get("similarity_distance", 0)
                    print(f"   {idx}. {title} - {artist} (расстояние: {distance:.2f})")
            else:
                print("❌ Не найдено результатов")
                
        except Exception as e:
            print(f"❌ Ошибка при поиске: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ Тест завершён успешно!")
    print("=" * 60)
    print("\n💡 Система поиска работает с Google API!")
    print("   Можно использовать для поиска песен по смыслу.")


if __name__ == "__main__":
    test_with_existing_logic()

