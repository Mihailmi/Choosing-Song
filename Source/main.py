"""
Основной скрипт для поиска и выбора песен.
Использует готовые embeddings для поиска и LLM для выбора лучшей песни.
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


def print_song_info(song: dict):
    """Красиво выводит информацию о песне."""
    print("\n" + "="*60)
    if song.get("title"):
        print(f"🎵 Название: {song['title']}")
    if song.get("themes"):
        themes = song.get("themes", [])
        if isinstance(themes, str):
            themes = [themes]
        print(f"🏷️  Темы: {', '.join(themes)}")
    if song.get("mood"):
        mood = song.get("mood", [])
        if isinstance(mood, str):
            mood = [mood]
        print(f"😊 Настроение: {', '.join(mood)}")
    if song.get("lyrics"):
        lyrics = song["lyrics"]
        # Обработка lyrics - может быть строкой или массивом
        if isinstance(lyrics, list):
            lyrics = "\n".join(lyrics)
        if len(lyrics) > 200:
            lyrics = lyrics[:200] + "..."
        print(f"\n📝 Текст:\n{lyrics}")
    print("="*60)


def main():
    """Основная функция для поиска и выбора песен."""
    
    # Пути к файлам
    project_root = Path(__file__).parent.parent
    index_path = project_root / "Data" / "songs_index.faiss"
    metadata_path = project_root / "Data" / "songs_metadata.json"
    
    # Проверка наличия индекса
    if not index_path.exists() or not metadata_path.exists():
        print("❌ Индекс не найден!")
        print("Сначала запустите prepare_embeddings.py для создания индекса.")
        sys.exit(1)
    
    # Проверка API ключа
    google_api_key = os.getenv("GOOGLE_API_KEY")
    
    if not google_api_key:
        print("❌ GOOGLE_API_KEY не установлен!")
        print("Создайте файл .env и добавьте: GOOGLE_API_KEY=your_key_here")
        sys.exit(1)
    
    print("🎵 Система выбора песен на основе RAG")
    print("="*60)
    
    # Инициализация компонентов
    print("\n🔧 Загрузка индекса...")
    embeddings_manager = EmbeddingsManager(api_key=google_api_key)
    embeddings_manager.load_index(str(index_path), str(metadata_path))
    
    search_engine = SongSearch(embeddings_manager)
    selector = SongSelector(api_key=google_api_key)
    
    print("✅ Система готова к работе!\n")
    
    # Интерактивный режим
    while True:
        try:
            print("\n" + "-"*60)
            query = input("Введите ваш запрос (или 'exit' для выхода): ").strip()
            
            if query.lower() in ['exit', 'quit', 'выход']:
                print("\n👋 До свидания!")
                break
            
            if not query:
                print("⚠️  Запрос не может быть пустым!")
                continue
            
            print(f"\n🔍 Ищу песни по запросу: '{query}'...")
            
            # Поиск кандидатов
            candidates = search_engine.search(query, k=5)
            
            if not candidates:
                print("❌ Не найдено подходящих песен.")
                continue
            
            print(f"\n✅ Найдено {len(candidates)} подходящих песен")
            print("\n📋 Кандидаты:")
            for idx, song in enumerate(candidates, 1):
                title = song.get("title", "Без названия")
                print(f"  {idx}. {title}")
            
            # Выбор лучшей песни через LLM
            print("\n🧠 Анализирую и выбираю лучшую песню...")
            result = selector.choose_best(query, candidates)
            
            # Вывод результата
            print("\n" + "⭐"*30)
            print("🎯 ВЫБРАННАЯ ПЕСНЯ:")
            print_song_info(result["song"])
            
            if result.get("reasoning"):
                print("\n💭 ОБЪЯСНЕНИЕ ВЫБОРА:")
                print(result["reasoning"])
            
            print("\n" + "⭐"*30)
            
        except KeyboardInterrupt:
            print("\n\n👋 До свидания!")
            break
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()

