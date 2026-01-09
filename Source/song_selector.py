"""
Модуль для выбора лучшей песни из кандидатов с помощью LLM.
Использует reasoning LLM для анализа и выбора оптимальной песни.
"""

import os
import requests
import time
import json
import asyncio
import aiohttp
from typing import List, Dict, Any


class SongSelector:
    """Класс для выбора лучшей песни из кандидатов через LLM."""
    
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash-lite", fallback_models: List[str] = None, max_retries: int = 2):
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
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash",
                "gemini-2.0-flash-lite",
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
        
        # Создание промпта с Few-shot Learning
        prompt = f"""Ты христианский эксперт по выбору христианской музыки, который помогает христианским пользователям найти идеальную песню для их настроения и ситуации.

Примеры правильных ответов:

Запрос: "Хочу спокойную песню для вечера"
Кандидаты:
1. Название: Тихая ночь
   Текст: Спокойная мелодия для вечернего времени...
   Настроение: спокойная, умиротворённая
2. Название: Утренняя радость
   Текст: Энергичная песня для начала дня...
   Настроение: энергичная, радостная
ВЫБОР: 1
ОБЪЯСНЕНИЕ: Песня "Тихая ночь" идеально подходит для вечера, так как она спокойная и создаёт атмосферу умиротворения, что соответствует запросу пользователя.

---

Запрос: "Нужна песня про любовь и расставание"
Кандидаты:
1. Название: Прощание
   Текст: Текст о расставании с любимым...
   Темы: любовь, расставание
2. Название: Новая встреча
   Текст: Песня о новой любви...
   Темы: любовь, надежда
ВЫБОР: 1
ОБЪЯСНЕНИЕ: Песня "Прощание" наиболее точно соответствует запросу, так как она сочетает темы любви и расставания, что точно отражает желание пользователя.

---

Теперь выбери для этого запроса:
"{user_query}"

Вот несколько подходящих христианских песен, найденных по смыслу:
{candidates_text}

Твоя задача:
1. Выбери ОДНУ лучшую христианскую песню, которая наиболее точно соответствует запросу пользователя
2. Объясни, почему именно эта христианская песня подходит лучше всего

Ответь в следующем формате:
ВЫБОР: [номер песни]
ОБЪЯСНЕНИЕ: [подробное объяснение, почему эта христианская песня лучше всего подходит запросу пользователя]"""

        try:
            # Формируем полный промпт
            full_prompt = prompt
            
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': self.api_key
            }
            
            # Используем Structured Output (JSON режим) если поддерживается
            # Для Gemini используем responseSchema
            payload = {
                "contents": [{
                    "parts": [{"text": full_prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "responseMimeType": "application/json",
                    "responseSchema": {
                        "type": "object",
                        "properties": {
                            "selected_index": {
                                "type": "integer",
                                "description": "Номер выбранной песни (1-based)"
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Подробное объяснение, почему эта песня лучше всего подходит запросу пользователя"
                            },
                            "confidence": {
                                "type": "number",
                                "description": "Уверенность в выборе от 0 до 1"
                            }
                        },
                        "required": ["selected_index", "reasoning"]
                    }
                }
            }
            
            # Пытаемся выполнить запрос с автоматическим переключением моделей
            api_result = self._try_request_with_fallback(payload, headers)
            response_text = api_result["candidates"][0]["content"]["parts"][0]["text"]
            
            # Пытаемся распарсить JSON ответ
            try:
                json_response = json.loads(response_text)
                selected_index = json_response.get("selected_index")
                reasoning = json_response.get("reasoning", "")
                confidence = json_response.get("confidence", 0.5)
            except (json.JSONDecodeError, KeyError):
                # Если JSON не распарсился, используем старый метод парсинга
                reasoning = response_text
                selected_index = self._parse_selection(reasoning, len(candidates))
                confidence = 0.5
            
            if selected_index is None or not (1 <= selected_index <= len(candidates)):
                # Если не удалось распарсить, берём первую песню
                selected_song = candidates[0]
                if not reasoning:
                    reasoning = "Не удалось определить выбор автоматически. Возвращена первая найденная песня."
            else:
                selected_song = candidates[selected_index - 1]
            
            result = {
                "song": selected_song,
                "reasoning": reasoning if return_reasoning else None,
                "confidence": confidence
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
    
    async def choose_best_async(
        self,
        user_query: str,
        candidates: List[Dict[str, Any]],
        session: aiohttp.ClientSession,
        return_reasoning: bool = True
    ) -> Dict[str, Any]:
        """
        Асинхронная версия choose_best.
        
        Args:
            user_query: Запрос пользователя
            candidates: Список кандидатов (песен)
            session: aiohttp сессия
            return_reasoning: Возвращать ли объяснение выбора
            
        Returns:
            Словарь с выбранной песней и объяснением
        """
        if not candidates:
            raise ValueError("Список кандидатов пуст!")
        
        # Форматирование списка кандидатов
        candidates_text = ""
        for idx, song in enumerate(candidates, 1):
            candidates_text += self._format_song_info(song, idx)
        
        # Создание промпта (тот же, что и в синхронной версии)
        prompt = f"""Ты христианский эксперт по выбору христианской музыки, который помогает христианским пользователям найти идеальную песню для их настроения и ситуации.

Примеры правильных ответов:

Запрос: "Хочу спокойную песню для вечера"
Кандидаты:
1. Название: Тихая ночь
   Текст: Спокойная мелодия для вечернего времени...
   Настроение: спокойная, умиротворённая
2. Название: Утренняя радость
   Текст: Энергичная песня для начала дня...
   Настроение: энергичная, радостная
ВЫБОР: 1
ОБЪЯСНЕНИЕ: Песня "Тихая ночь" идеально подходит для вечера, так как она спокойная и создаёт атмосферу умиротворения, что соответствует запросу пользователя.

---

Теперь выбери для этого запроса:
"{user_query}"

Вот несколько подходящих христианских песен, найденных по смыслу:
{candidates_text}

Твоя задача:
1. Выбери ОДНУ лучшую христианскую песню, которая наиболее точно соответствует запросу пользователя
2. Объясни, почему именно эта христианская песня подходит лучше всего

Ответь в следующем формате:
ВЫБОР: [номер песни]
ОБЪЯСНЕНИЕ: [подробное объяснение, почему эта христианская песня лучше всего подходит запросу пользователя]"""
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': self.api_key
            }
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "responseMimeType": "application/json",
                    "responseSchema": {
                        "type": "object",
                        "properties": {
                            "selected_index": {
                                "type": "integer",
                                "description": "Номер выбранной песни (1-based)"
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Подробное объяснение выбора"
                            },
                            "confidence": {
                                "type": "number",
                                "description": "Уверенность в выборе от 0 до 1"
                            }
                        },
                        "required": ["selected_index", "reasoning"]
                    }
                }
            }
            
            # Асинхронный запрос
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            async with session.post(api_url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
                
                api_result = await response.json()
                response_text = api_result["candidates"][0]["content"]["parts"][0]["text"]
                
                # Парсинг JSON
                try:
                    json_response = json.loads(response_text)
                    selected_index = json_response.get("selected_index")
                    reasoning = json_response.get("reasoning", "")
                    confidence = json_response.get("confidence", 0.5)
                except (json.JSONDecodeError, KeyError):
                    reasoning = response_text
                    selected_index = self._parse_selection(reasoning, len(candidates))
                    confidence = 0.5
                
                if selected_index is None or not (1 <= selected_index <= len(candidates)):
                    selected_song = candidates[0]
                    if not reasoning:
                        reasoning = "Не удалось определить выбор автоматически."
                else:
                    selected_song = candidates[selected_index - 1]
                
                return {
                    "song": selected_song,
                    "reasoning": reasoning if return_reasoning else None,
                    "confidence": confidence
                }
                
        except Exception as e:
            print(f"Ошибка при выборе песни: {e}")
            return {
                "song": candidates[0],
                "reasoning": "Произошла ошибка при анализе. Возвращена первая найденная песня.",
                "confidence": 0.0
            }
    
    async def choose_best_batch(
        self,
        queries: List[str],
        candidates_list: List[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Batch обработка нескольких запросов одновременно.
        
        Args:
            queries: Список запросов пользователей
            candidates_list: Список списков кандидатов для каждого запроса
            
        Returns:
            Список результатов для каждого запроса
        """
        if len(queries) != len(candidates_list):
            raise ValueError("Количество запросов должно совпадать с количеством списков кандидатов")
        
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.choose_best_async(query, candidates, session)
                for query, candidates in zip(queries, candidates_list)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Обрабатываем исключения
            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    processed_results.append({
                        "song": None,
                        "reasoning": f"Ошибка: {str(result)}",
                        "confidence": 0.0
                    })
                else:
                    processed_results.append(result)
            
            return processed_results

