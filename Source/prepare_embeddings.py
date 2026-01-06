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
    
    # Пути к файлам
    project_root = Path(__file__).parent.parent
    songs_path = project_root / "Data" / "Songs.json"
    index_path = project_root / "Data" / "songs_index.faiss"
    metadata_path = project_root / "Data" / "songs_metadata.json"
    
    # Проверка наличия файла с песнями
    if not songs_path.exists():
        print(f"❌ Файл {songs_path} не найден!")
        sys.exit(1)
    
    # Проверка API ключа
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY не установлен!")
        print("Создайте файл .env и добавьте: OPENAI_API_KEY=your_key_here")
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
        
    except Exception as e:
        print(f"❌ Ошибка при загрузке файла: {e}")
        sys.exit(1)
    
    # Создание менеджера embeddings
    print("\n🔧 Инициализация EmbeddingsManager...")
    manager = EmbeddingsManager(api_key=api_key)
    
    # Создание embeddings
    print("\n🧠 Создание embeddings (это может занять время)...")
    vectors = manager.create_embeddings(songs)
    
    if not vectors:
        print("❌ Не удалось создать embeddings!")
        sys.exit(1)
    
    # Построение индекса
    print("\n📊 Построение FAISS индекса...")
    manager.build_index(vectors)
    
    # Сохранение
    print("\n💾 Сохранение индекса и метаданных...")
    manager.save_index(str(index_path), str(metadata_path))
    
    print("\n✅ Готово! Embeddings успешно созданы и сохранены.")
    print(f"📁 Индекс: {index_path}")
    print(f"📁 Метаданные: {metadata_path}")
    print("\nТеперь можно использовать систему поиска песен!")


if __name__ == "__main__":
    main()

