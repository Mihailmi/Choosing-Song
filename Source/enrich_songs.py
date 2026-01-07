"""
Скрипт для обогащения данных песен полями themes и mood.
Использует LLM для автоматического извлечения тем и настроения из текста песен.
Это опционально - система работает и без этих полей!
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from typing import List, Dict, Any

# Загрузка переменных окружения
load_dotenv()

# Добавляем путь к Source для импорта модулей
sys.path.insert(0, str(Path(__file__).parent))


def extract_themes_and_mood(client: OpenAI, song: Dict[str, Any], model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """
    Извлекает themes и mood из песни с помощью LLM.
    
    Args:
        client: OpenAI клиент
        song: Словарь с данными песни
        model: Модель для использования
        
    Returns:
        Словарь с themes и mood
    """
    # Подготовка текста
    text_parts = []
    if song.get("title"):
        text_parts.append(f"Название: {song['title']}")
    
    if song.get("lyrics"):
        lyrics = song["lyrics"]
        if isinstance(lyrics, list):
            lyrics = "\n".join(lyrics)
        text_parts.append(f"Текст:\n{lyrics}")
    
    song_text = "\n".join(text_parts)
    
    prompt = f"""Проанализируй эту песню и определи:

1. Темы (themes) - основные темы и идеи песни (3-5 ключевых слов/фраз)
2. Настроение (mood) - эмоциональное настроение песни (2-3 слова)

Песня:
{song_text}

Ответь ТОЛЬКО в формате JSON (без дополнительного текста):
{{
  "themes": ["тема1", "тема2", "тема3"],
  "mood": ["настроение1", "настроение2"]
}}"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Ты эксперт по анализу музыки. Извлекай темы и настроение из песен. Отвечай только валидным JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return {
            "themes": result.get("themes", []),
            "mood": result.get("mood", [])
        }
    except Exception as e:
        print(f"Ошибка при обработке песни {song.get('title', 'Unknown')}: {e}")
        return {"themes": [], "mood": []}


def enrich_songs(songs: List[Dict[str, Any]], api_key: str, batch_size: int = 10) -> List[Dict[str, Any]]:
    """
    Обогащает список песен полями themes и mood.
    
    Args:
        songs: Список песен
        api_key: OpenAI API ключ
        batch_size: Размер батча для обработки (для вывода прогресса)
        
    Returns:
        Обогащённый список песен
    """
    client = OpenAI(api_key=api_key)
    enriched = []
    
    print(f"🎵 Обогащение {len(songs)} песен...")
    print("⚠️  Это займёт время и потратит токены OpenAI API!")
    print("💡 Совет: можно обогатить только часть песен для теста\n")
    
    for idx, song in enumerate(songs):
        # Пропускаем, если уже есть themes и mood
        if song.get("themes") and song.get("mood"):
            enriched.append(song)
            if (idx + 1) % batch_size == 0:
                print(f"Пропущено {idx + 1}/{len(songs)} (уже обогащены)")
            continue
        
        # Извлекаем themes и mood
        extracted = extract_themes_and_mood(client, song)
        
        # Добавляем к песне
        song_copy = song.copy()
        song_copy["themes"] = extracted["themes"]
        song_copy["mood"] = extracted["mood"]
        enriched.append(song_copy)
        
        if (idx + 1) % batch_size == 0:
            print(f"Обработано {idx + 1}/{len(songs)} песен...")
            print(f"  Пример: {song.get('title', 'Unknown')} -> themes: {extracted['themes'][:2] if extracted['themes'] else '[]'}")
    
    print(f"\n✅ Обогащено {len(enriched)} песен!")
    return enriched


def main():
    """Основная функция."""
    project_root = Path(__file__).parent.parent
    songs_path = project_root / "Data" / "Songs.json"
    output_path = project_root / "Data" / "Songs_enriched.json"
    
    # Проверка файла
    if not songs_path.exists():
        print(f"❌ Файл {songs_path} не найден!")
        sys.exit(1)
    
    # Проверка API ключа
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY не установлен!")
        print("Создайте файл .env и добавьте: OPENAI_API_KEY=your_key_here")
        sys.exit(1)
    
    # Загрузка песен
    print(f"📖 Загрузка песен из {songs_path}...")
    with open(songs_path, 'r', encoding='utf-8') as f:
        songs = json.load(f)
    
    if isinstance(songs, dict):
        if "songs" in songs:
            songs = songs["songs"]
        elif "data" in songs:
            songs = songs["data"]
    
    if not isinstance(songs, list):
        print("❌ Неверный формат данных!")
        sys.exit(1)
    
    print(f"✅ Загружено {len(songs)} песен\n")
    
    # Подтверждение
    response = input("Продолжить обогащение? Это займёт время и потратит токены. (yes/no): ")
    if response.lower() not in ['yes', 'y', 'да', 'д']:
        print("Отменено.")
        sys.exit(0)
    
    # Обогащение
    enriched_songs = enrich_songs(songs, api_key)
    
    # Сохранение
    print(f"\n💾 Сохранение в {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enriched_songs, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Готово! Обогащённые данные сохранены в {output_path}")
    print("\n💡 Теперь можно использовать обогащённый файл вместо исходного.")


if __name__ == "__main__":
    main()

