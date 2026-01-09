"""
Модуль для поиска песен по запросу пользователя.
Использует векторный поиск для нахождения релевантных песен.
"""

import numpy as np
import re
from typing import List, Dict, Any
from collections import Counter
from embeddings_manager import EmbeddingsManager


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
        
        # Подготовка данных для keyword поиска
        self._prepare_keyword_index()
    
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
    ) -> List[Dict[str, Any]]:
        """
        Поиск с дополнительными фильтрами.
        
        Args:
            query: Текст запроса пользователя
            k: Количество песен для возврата
            language: Фильтр по языку (например, "ru", "en")
            mood: Список настроений для фильтрации
            
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
            
            filtered.append(song)
            
            if len(filtered) >= k:
                break
        
        return filtered
    
    def _prepare_keyword_index(self):
        """Подготавливает индекс для keyword поиска."""
        self.song_texts = []
        for metadata in self.embeddings_manager.vectors_metadata:
            song = metadata["metadata"]
            # Собираем весь текст песни для keyword поиска
            text_parts = []
            if song.get("title"):
                text_parts.append(song["title"].lower())
            if song.get("lyrics"):
                lyrics = song["lyrics"]
                if isinstance(lyrics, list):
                    lyrics = " ".join(lyrics)
                text_parts.append(str(lyrics).lower())
            if song.get("themes"):
                themes = song.get("themes", [])
                if isinstance(themes, str):
                    themes = [themes]
                text_parts.extend([t.lower() for t in themes])
            if song.get("mood"):
                mood = song.get("mood", [])
                if isinstance(mood, str):
                    mood = [mood]
                text_parts.extend([m.lower() for m in mood])
            
            self.song_texts.append(" ".join(text_parts))
    
    def _tokenize(self, text: str) -> List[str]:
        """Простая токенизация текста."""
        # Удаляем знаки препинания и разбиваем на слова
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()
        # Удаляем очень короткие слова
        return [w for w in words if len(w) > 2]
    
    def _keyword_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Простой keyword поиск на основе TF (term frequency).
        
        Args:
            query: Текст запроса
            k: Количество результатов
            
        Returns:
            Список песен с оценкой релевантности
        """
        query_words = set(self._tokenize(query))
        if not query_words:
            return []
        
        scores = []
        for idx, song_text in enumerate(self.song_texts):
            song_words = self._tokenize(song_text)
            word_counts = Counter(song_words)
            
            # Подсчитываем совпадения
            matches = sum(word_counts.get(word, 0) for word in query_words)
            # Нормализуем по длине текста
            score = matches / max(len(song_words), 1)
            
            if score > 0:
                song_data = self.embeddings_manager.vectors_metadata[idx]["metadata"].copy()
                song_data["keyword_score"] = score
                scores.append((score, song_data))
        
        # Сортируем по убыванию score
        scores.sort(reverse=True, key=lambda x: x[0])
        return [song for _, song in scores[:k]]
    
    def hybrid_search(self, query: str, k: int = 5, semantic_weight: float = 0.7, keyword_weight: float = 0.3) -> List[Dict[str, Any]]:
        """
        Гибридный поиск: комбинация семантического и keyword поиска.
        
        Args:
            query: Текст запроса
            k: Количество результатов
            semantic_weight: Вес семантического поиска (0-1)
            keyword_weight: Вес keyword поиска (0-1)
            
        Returns:
            Список песен, отсортированных по релевантности
        """
        # Семантический поиск
        semantic_results = self.search(query, k=k * 2)
        
        # Keyword поиск
        keyword_results = self._keyword_search(query, k=k * 2)
        
        # Создаём словарь для объединения результатов
        combined_scores = {}
        
        # Добавляем результаты семантического поиска
        for idx, song in enumerate(semantic_results):
            song_id = song.get("id", id(song))
            distance = song.get("similarity_distance", 1.0)
            # Преобразуем расстояние в score (меньше расстояние = выше score)
            semantic_score = 1.0 / (1.0 + distance)
            combined_scores[song_id] = {
                "song": song,
                "semantic_score": semantic_score,
                "keyword_score": 0.0
            }
        
        # Добавляем результаты keyword поиска
        for song in keyword_results:
            song_id = song.get("id", id(song))
            keyword_score = song.get("keyword_score", 0.0)
            
            if song_id in combined_scores:
                combined_scores[song_id]["keyword_score"] = keyword_score
            else:
                combined_scores[song_id] = {
                    "song": song,
                    "semantic_score": 0.0,
                    "keyword_score": keyword_score
                }
        
        # Нормализуем scores
        if combined_scores:
            max_semantic = max(s["semantic_score"] for s in combined_scores.values()) or 1.0
            max_keyword = max(s["keyword_score"] for s in combined_scores.values()) or 1.0
            
            for song_id in combined_scores:
                s = combined_scores[song_id]
                if max_semantic > 0:
                    s["semantic_score"] /= max_semantic
                if max_keyword > 0:
                    s["keyword_score"] /= max_keyword
        
        # Вычисляем итоговый score
        final_results = []
        for song_id, data in combined_scores.items():
            final_score = (semantic_weight * data["semantic_score"] + 
                          keyword_weight * data["keyword_score"])
            song = data["song"].copy()
            song["hybrid_score"] = final_score
            song["similarity_distance"] = data["song"].get("similarity_distance", 1.0)
            final_results.append((final_score, song))
        
        # Сортируем по убыванию итогового score
        final_results.sort(reverse=True, key=lambda x: x[0])
        return [song for _, song in final_results[:k]]

