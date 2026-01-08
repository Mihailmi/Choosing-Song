"""
Модуль для выбора лучшей песни из кандидатов с помощью LLM.
Использует reasoning LLM для анализа и выбора оптимальной песни.
"""

import os
import requests
import time
from typing import List, Dict, Any


class SongSelector:
    """Класс для выбора лучшей песни из кандидатов через LLM."""
    
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash", fallback_models: List[str] = None, max_retries: int = 2):
        """
        Инициализация селектора песен.
        
        Args:
            api_key: Google API ключ. Если не указан, берётся из переменной окружения GOOGLE_API_KEY.
            model: Модель LLM для использования (по умолчанию gemini-2.5-flash)
            fallback_models: Список резервных моделей для автоматического переключения при ошибках
            max_retries: Максимальное количество повторных попыток для одной модели при перегрузке
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY не установлен")
        
        self.model = model
        self.max_retries = max_retries
        # Резервные модели по умолчанию (от быстрых к более мощным)
        if fallback_models is None:
            self.fallback_models = [
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-2.5-pro",
                "gemini-1.5-pro",
                "gemini-flash-latest",
                "gemini-pro-latest"
            ]
        else:
            self.fallback_models = fallback_models
        
        # Убедимся, что основная модель в списке для попыток
        self.models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    def _format_song_info(self, song: Dict[str, Any], index: int) -> str:
        """
        Форматирует информацию о песне для промпта.
        
        Args:
            song: Словарь с данными песни
            index: Индекс песни в списке
            
        Returns:
            Отформатированная строка с информацией о песне
        """
        info = f"\n{index}. "
        
        if song.get("title"):
            info += f"Название: {song['title']}"
        if song.get("lyrics"):
            lyrics = song["lyrics"]
            # Обработка lyrics - может быть строкой или массивом
            if isinstance(lyrics, list):
                lyrics = "\n".join(lyrics)
            # Ограничиваем длину текста
            if len(lyrics) > 300:
                lyrics = lyrics[:300] + "..."
            info += f"\n   Текст: {lyrics}"
        if song.get("themes"):
            themes = song.get("themes", [])
            if isinstance(themes, str):
                themes = [themes]
            info += f"\n   Темы: {', '.join(themes)}"
        if song.get("mood"):
            mood = song.get("mood", [])
            if isinstance(mood, str):
                mood = [mood]
            info += f"\n   Настроение: {', '.join(mood)}"
        
        return info
    
    def _is_overload_error(self, response: requests.Response) -> bool:
        """
        Проверяет, является ли ошибка ошибкой перегрузки модели.
        
        Args:
            response: Ответ от API
            
        Returns:
            True, если это ошибка перегрузки
        """
        error_text = response.text.lower()
        status_code = response.status_code
        
        # Проверяем статус коды, указывающие на перегрузку
        is_overload_status = status_code in [429, 503, 500]
        
        # Проверяем текст ошибки
        is_overload_text = (
            "overloaded" in error_text or
            "overload" in error_text or
            "too many requests" in error_text or
            "rate limit" in error_text or
            "service unavailable" in error_text or
            "temporarily unavailable" in error_text or
            "try again later" in error_text
        )
        
        return is_overload_status or is_overload_text
    
    def _is_model_error(self, response: requests.Response) -> bool:
        """
        Проверяет, является ли ошибка ошибкой модели (не найдена, не поддерживается).
        
        Args:
            response: Ответ от API
            
        Returns:
            True, если это ошибка модели
        """
        error_text = response.text.lower()
        status_code = response.status_code
        
        return (
            status_code == 404 or
            "not found" in error_text or
            "not supported" in error_text or
            ("model" in error_text and ("not found" in error_text or "not supported" in error_text))
        )
    
    def _try_request_with_fallback(self, payload: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Пытается выполнить запрос к API, переключаясь между моделями при ошибках.
        При перегрузке модели делает несколько попыток с задержкой перед переключением.
        
        Args:
            payload: Тело запроса
            headers: Заголовки запроса
            
        Returns:
            Ответ от API в формате JSON
            
        Raises:
            Exception: Если все модели недоступны
        """
        last_error = None
        
        for model_name in self.models_to_try:
            # Пытаемся использовать текущую модель с повторными попытками при перегрузке
            for retry in range(self.max_retries + 1):
                try:
                    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                    response = requests.post(api_url, headers=headers, json=payload)
                    
                    if response.status_code == 200:
                        # Успешный запрос
                        if model_name != self.model:
                            print(f"  ⚠️  Переключился на модель: {model_name}")
                        return response.json()
                    
                    # Обработка ошибок
                    if self._is_overload_error(response):
                        # Модель перегружена - делаем повторную попытку с задержкой
                        if retry < self.max_retries:
                            wait_time = (retry + 1) * 2  # Экспоненциальная задержка: 2, 4, 6 секунд
                            print(f"  ⏳ Модель {model_name} перегружена, повторная попытка через {wait_time} сек... (попытка {retry + 1}/{self.max_retries})")
                            time.sleep(wait_time)
                            continue
                        else:
                            # Исчерпаны попытки для этой модели, пробуем следующую
                            last_error = f"{response.status_code}: {response.text[:200]}"
                            print(f"  ⚠️  Модель {model_name} перегружена после {self.max_retries + 1} попыток, пробуем следующую...")
                            break
                    
                    elif self._is_model_error(response):
                        # Ошибка модели (не найдена, не поддерживается) - сразу пробуем следующую
                        last_error = f"{response.status_code}: {response.text[:200]}"
                        print(f"  ⚠️  Модель {model_name} недоступна, пробуем следующую...")
                        break
                    
                    else:
                        # Другая ошибка (квота, авторизация и т.д.) - пробрасываем
                        error_msg = response.text[:500] if len(response.text) > 500 else response.text
                        raise Exception(f"{response.status_code}: {error_msg}")
                        
                except requests.exceptions.RequestException as e:
                    # Сетевая ошибка
                    if retry < self.max_retries:
                        wait_time = (retry + 1) * 1
                        print(f"  ⏳ Сетевая ошибка для {model_name}, повторная попытка через {wait_time} сек...")
                        time.sleep(wait_time)
                        continue
                    else:
                        last_error = str(e)
                        print(f"  ⚠️  Сетевая ошибка для {model_name}, пробуем следующую модель...")
                        break
        
        # Все модели не сработали
        raise Exception(f"Все модели недоступны. Последняя ошибка: {last_error}")
    
    def choose_best(
        self, 
        user_query: str, 
        candidates: List[Dict[str, Any]],
        return_reasoning: bool = True
    ) -> Dict[str, Any]:
        """
        Выбирает лучшую песню из кандидатов на основе запроса пользователя.
        
        Args:
            user_query: Запрос пользователя
            candidates: Список кандидатов (песен)
            return_reasoning: Возвращать ли объяснение выбора
            
        Returns:
            Словарь с выбранной песней и объяснением (если return_reasoning=True)
        """
        if not candidates:
            raise ValueError("Список кандидатов пуст!")
        
        # Форматирование списка кандидатов
        candidates_text = ""
        for idx, song in enumerate(candidates, 1):
            candidates_text += self._format_song_info(song, idx)
        
        # Создание промпта
        prompt = f"""Ты помощник по выбору музыки. Пользователь хочет найти песню по следующему описанию:

"{user_query}"

Вот несколько подходящих песен, найденных по смыслу:
{candidates_text}

Твоя задача:
1. Выбери ОДНУ лучшую песню, которая наиболее точно соответствует запросу пользователя
2. Объясни, почему именно эта песня подходит лучше всего

Ответь в следующем формате:
ВЫБОР: [номер песни]
ОБЪЯСНЕНИЕ: [подробное объяснение, почему эта песня лучше всего подходит запросу пользователя]"""

        try:
            # Формируем полный промпт с системным сообщением
            full_prompt = """Ты эксперт по музыке, который помогает пользователям найти идеальную песню для их настроения и ситуации.

""" + prompt
            
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': self.api_key
            }
            payload = {
                "contents": [{
                    "parts": [{"text": full_prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7
                }
            }
            
            # Пытаемся выполнить запрос с автоматическим переключением моделей
            result = self._try_request_with_fallback(payload, headers)
            reasoning = result["candidates"][0]["content"]["parts"][0]["text"]
            
            # Парсинг ответа для извлечения номера выбранной песни
            selected_index = self._parse_selection(reasoning, len(candidates))
            
            if selected_index is None:
                # Если не удалось распарсить, берём первую песню
                selected_song = candidates[0]
            else:
                selected_song = candidates[selected_index - 1]
            
            result = {
                "song": selected_song,
                "reasoning": reasoning if return_reasoning else None
            }
            
            return result
            
        except Exception as e:
            print(f"Ошибка при выборе песни: {e}")
            # В случае ошибки возвращаем первую песню
            return {
                "song": candidates[0],
                "reasoning": "Произошла ошибка при анализе. Возвращена первая найденная песня."
            }
    
    def _parse_selection(self, reasoning: str, max_index: int) -> int:
        """
        Парсит ответ LLM для извлечения номера выбранной песни.
        
        Args:
            reasoning: Текст ответа от LLM
            max_index: Максимальный допустимый индекс
            
        Returns:
            Номер выбранной песни (1-based) или None
        """
        import re
        
        # Ищем паттерны типа "ВЫБОР: 1" или "1." или просто число в начале
        patterns = [
            r'ВЫБОР:\s*(\d+)',
            r'выбор:\s*(\d+)',
            r'Выбор:\s*(\d+)',
            r'^(\d+)\.',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, reasoning, re.IGNORECASE | re.MULTILINE)
            if match:
                num = int(match.group(1))
                if 1 <= num <= max_index:
                    return num
        
        # Если не нашли явного указания, ищем числа в тексте
        numbers = re.findall(r'\b(\d+)\b', reasoning)
        for num_str in numbers:
            num = int(num_str)
            if 1 <= num <= max_index:
                return num
        
        return None

