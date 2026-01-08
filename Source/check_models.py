"""
Скрипт для проверки доступных моделей Google Gemini API.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def list_available_models():
    """Получает список доступных моделей из Google API."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY не найден в .env")
        return
    
    url = "https://generativelanguage.googleapis.com/v1beta/models"
    headers = {
        'X-goog-api-key': api_key
    }
    
    print("🔍 Запрос списка доступных моделей...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        models = response.json()
        print("\n✅ Доступные модели:\n")
        
        # Группируем модели по типу
        generate_models = []
        embed_models = []
        
        for model in models.get("models", []):
            name = model.get("name", "").replace("models/", "")
            supported_methods = model.get("supportedGenerationMethods", [])
            
            if "generateContent" in supported_methods:
                generate_models.append((name, model))
            if "embedContent" in supported_methods:
                embed_models.append((name, model))
        
        print("📝 Модели для generateContent (LLM):")
        for name, model in generate_models:
            display_name = model.get("displayName", "")
            description = model.get("description", "")
            print(f"  ✅ {name}")
            if display_name:
                print(f"     Название: {display_name}")
            if description:
                print(f"     Описание: {description[:100]}...")
            print()
        
        print("\n🔢 Модели для embedContent (embeddings):")
        for name, model in embed_models:
            display_name = model.get("displayName", "")
            print(f"  ✅ {name}")
            if display_name:
                print(f"     Название: {display_name}")
            print()
        
        # Рекомендации
        if generate_models:
            print("\n💡 Рекомендуемые модели для использования:")
            recommended = [name for name, _ in generate_models if "flash" in name.lower() or "1.5" in name]
            if recommended:
                print(f"  🎯 {recommended[0]} (быстрая и эффективная)")
            else:
                print(f"  🎯 {generate_models[0][0]} (первая доступная)")
        
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    list_available_models()

