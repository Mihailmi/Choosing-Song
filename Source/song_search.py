"""
Модуль для поиска песен по запросу пользователя.
Использует векторный поиск для нахождения релевантных песен.
"""

import numpy as np
from typing import List, Dict, Any
from .embeddings_manager import EmbeddingsManager


class SongSearch:
    """Класс для поиска песен по семантическому запросу."""
    
    def __init__(self, embeddings_manager: EmbeddingsManager):
        """
        Инициализация поисковой системы.
        
        Args:
            embeddings_manager: Экземпляр EmbeddingsManager с загруженным индексом
        """
        self.embeddings_manager = embeddings_manager
        
        if embeddings_manager.index is None:
            raise ValueError("Индекс не загружен! Сначала загрузите индекс.")
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Ищет k наиболее релевантных песен по запросу.
        
        Args:
            query: Текст запроса пользователя
            k: Количество песен для возврата (по умолчанию 5)
            
        Returns:
            Список словарей с данными песен, отсортированных по релевантности
        """
        # Создание embedding для запроса
        query_embedding = self.embeddings_manager.get_query_embedding(query)
        
        # Поиск в индексе
        distances, indices = self.embeddings_manager.index.search(query_embedding, k)
        
        # Получение метаданных найденных песен
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.embeddings_manager.vectors_metadata):
                song_data = self.embeddings_manager.vectors_metadata[idx]["metadata"].copy()
                song_data["similarity_distance"] = float(distance)
                results.append(song_data)
        
        return results
    
    def search_with_filters(
        self, 
        query: str, 
        k: int = 5,
        language: str = None,
        mood: List[str] = None,
        artist: str = None
    ) -> List[Dict[str, Any]]:
        """
        Поиск с дополнительными фильтрами.
        
        Args:
            query: Текст запроса пользователя
            k: Количество песен для возврата
            language: Фильтр по языку (например, "ru", "en")
            mood: Список настроений для фильтрации
            artist: Фильтр по исполнителю
            
        Returns:
            Отфильтрованный список песен
        """
        # Сначала получаем больше результатов для фильтрации
        candidates = self.search(query, k=k * 3)
        
        filtered = []
        for song in candidates:
            # Фильтр по языку
            if language and song.get("language") != language:
                continue
            
            # Фильтр по настроению
            if mood:
                song_moods = song.get("mood", [])
                if isinstance(song_moods, str):
                    song_moods = [song_moods]
                if not any(m in song_moods for m in mood):
                    continue
            
            # Фильтр по исполнителю
            if artist and song.get("artist", "").lower() != artist.lower():
                continue
            
            filtered.append(song)
            
            if len(filtered) >= k:
                break
        
        return filtered

