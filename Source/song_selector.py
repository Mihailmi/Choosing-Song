"""
Модуль для выбора лучшей песни из кандидатов с помощью LLM.
Использует reasoning LLM для анализа и выбора оптимальной песни.
"""

import os
from openai import OpenAI
from typing import List, Dict, Any


class SongSelector:
    """Класс для выбора лучшей песни из кандидатов через LLM."""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        """
        Инициализация селектора песен.
        
        Args:
            api_key: OpenAI API ключ. Если не указан, берётся из переменной окружения.
            model: Модель LLM для использования (по умолчанию gpt-4o-mini)
        """
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
    
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
        if song.get("artist"):
            info += f" | Исполнитель: {song['artist']}"
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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ты эксперт по музыке, который помогает пользователям найти идеальную песню для их настроения и ситуации."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7
            )
            
            reasoning = response.choices[0].message.content
            
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

