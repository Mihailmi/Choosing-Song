"""
Скрипт для первоначальной подготовки embeddings.
Запускается один раз для создания векторной БД из JSON файла с песнями.
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Добавляем путь к Source для импорта модулей
sys.path.insert(0, str(Path(__file__).parent))

from embeddings_manager import EmbeddingsManager

# Загрузка переменных окружения
load_dotenv()


def main():
    """Основная функция для подготовки embeddings."""
    
    # Параметры фильтрации (можно изменить или установить в None для отключения)
    FILTER_BY_ALBUM_ID = "63e65c7471da173056c1c595"  # Молодежный сборник (или None для всех песен)
    MAX_SONGS = None  # Максимальное количество песен (None = без ограничений, или число для ограничения)
    
    # Пути к файлам
    project_root = Path(__file__).parent.parent
    songs_path = project_root / "Data" / "Songs.json"
    enriched_path = project_root / "Data" / "Songs_enriched.json"
    index_path = project_root / "Data" / "songs_index.faiss"
    metadata_path = project_root / "Data" / "songs_metadata.json"
    
    # Используем обогащённый файл, если он есть
    if enriched_path.exists():
        songs_path = enriched_path
        print(f"💡 Найден обогащённый файл: {enriched_path}")
        print("   Будут использованы themes и mood, если они есть.\n")
    
    # Проверка наличия файла с песнями
    if not songs_path.exists():
        print(f"❌ Файл {songs_path} не найден!")
        sys.exit(1)
    
    # Проверка API ключа
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY не установлен!")
        print("Создайте файл .env и добавьте: GOOGLE_API_KEY=your_key_here")
        sys.exit(1)
    
    print("🚀 Начинаем подготовку embeddings...")
    print(f"📁 Файл с песнями: {songs_path}")
    
    # Загрузка песен
    print("\n📖 Загрузка песен из JSON...")
    try:
        with open(songs_path, 'r', encoding='utf-8') as f:
            songs = json.load(f)
        
        # Если это словарь, пытаемся найти список песен
        if isinstance(songs, dict):
            # Пробуем разные возможные ключи
            if "songs" in songs:
                songs = songs["songs"]
            elif "data" in songs:
                songs = songs["data"]
            else:
                # Берём первый список, который найдём
                for key, value in songs.items():
                    if isinstance(value, list):
                        songs = value
                        break
        
        if not isinstance(songs, list):
            raise ValueError("Не удалось найти список песен в JSON файле!")
        
        print(f"✅ Загружено {len(songs)} песен")
        
        # Фильтрация по albumId (если указан)
        if FILTER_BY_ALBUM_ID:
            original_count = len(songs)
            songs = [s for s in songs if s.get("albumId") == FILTER_BY_ALBUM_ID]
            print(f"🔍 Отфильтровано по albumId '{FILTER_BY_ALBUM_ID}': {len(songs)} песен (было {original_count})")
        
        # Ограничение количества
        if MAX_SONGS is not None and len(songs) > MAX_SONGS:
            print(f"✂️  Ограничение до {MAX_SONGS} песен (было {len(songs)})")
            songs = songs[:MAX_SONGS]
        
        if not songs:
            print("❌ Нет песен для обработки после фильтрации!")
            sys.exit(1)
        
        print(f"📊 Будет обработано: {len(songs)} песен")
        
    except Exception as e:
        print(f"❌ Ошибка при загрузке файла: {e}")
        sys.exit(1)
    
    # Создание менеджера embeddings
    print("\n🔧 Инициализация EmbeddingsManager...")
    manager = EmbeddingsManager(api_key=api_key)
    
    # Создание embeddings
    print("\n🧠 Создание embeddings (это может занять время)...")
    print(f"⏱️  Обработка {len(songs)} песен может занять несколько минут...")
    
    try:
        vectors = manager.create_embeddings(songs)
        
        if not vectors:
            print("❌ Не удалось создать embeddings!")
            print("   Проверьте подключение к интернету и валидность GOOGLE_API_KEY")
            sys.exit(1)
        
        if len(vectors) < len(songs):
            print(f"⚠️  Внимание: Создано только {len(vectors)} из {len(songs)} embeddings")
            print("   Некоторые песни могли быть пропущены из-за ошибок")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        print("   Частично созданные данные не сохранены")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка при создании embeddings: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Построение индекса
    print("\n📊 Построение FAISS индекса...")
    try:
        manager.build_index(vectors)
    except Exception as e:
        print(f"❌ Ошибка при построении индекса: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Проверка существующих файлов
    if index_path.exists() or metadata_path.exists():
        print(f"\n⚠️  Внимание: Файлы уже существуют!")
        print(f"   Индекс: {index_path.exists()}")
        print(f"   Метаданные: {metadata_path.exists()}")
        print("   Они будут перезаписаны.")
    
    # Сохранение
    print("\n💾 Сохранение индекса и метаданных...")
    try:
        # Создаём директорию, если её нет
        index_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        
        manager.save_index(str(index_path), str(metadata_path))
        
        print("\n✅ Готово! Embeddings успешно созданы и сохранены.")
        print(f"📁 Индекс: {index_path}")
        print(f"📁 Метаданные: {metadata_path}")
        print(f"📊 Всего песен в индексе: {len(vectors)}")
        print("\nТеперь можно использовать систему поиска песен!")
        
    except Exception as e:
        print(f"\n❌ Ошибка при сохранении файлов: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

