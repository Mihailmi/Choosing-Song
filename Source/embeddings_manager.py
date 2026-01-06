"""
Модуль для создания и управления embeddings песен.
Создаёт векторные представления песен один раз и сохраняет их в FAISS индекс.
"""

import json
import os
import numpy as np
import faiss
from openai import OpenAI
from typing import List, Dict, Any


class EmbeddingsManager:
    """Управляет созданием embeddings и векторной БД."""
    
    def __init__(self, api_key: str = None):
        """
        Инициализация менеджера embeddings.
        
        Args:
            api_key: OpenAI API ключ. Если не указан, берётся из переменной окружения OPENAI_API_KEY.
        """
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = "text-embedding-3-large"
        self.dimension = 3072  # Размерность для text-embedding-3-large
        self.index = None
        self.vectors_metadata = []
        
    def _prepare_song_text(self, song: Dict[str, Any]) -> str:
        """
        Подготавливает текст песни для создания embedding.
        
        Args:
            song: Словарь с данными песни
            
        Returns:
            Текст для embedding
        """
        text_parts = []
        
        if song.get("title"):
            text_parts.append(f"Название: {song['title']}")
        if song.get("artist"):
            text_parts.append(f"Исполнитель: {song['artist']}")
        if song.get("lyrics"):
            text_parts.append(f"Текст: {song['lyrics']}")
        if song.get("themes"):
            themes = song["themes"] if isinstance(song["themes"], list) else [song["themes"]]
            text_parts.append(f"Темы: {', '.join(themes)}")
        if song.get("mood"):
            mood = song["mood"] if isinstance(song["mood"], list) else [song["mood"]]
            text_parts.append(f"Настроение: {', '.join(mood)}")
            
        return "\n".join(text_parts)
    
    def create_embeddings(self, songs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Создаёт embeddings для всех песен.
        
        Args:
            songs: Список словарей с данными песен
            
        Returns:
            Список словарей с id, embedding и metadata
        """
        vectors = []
        
        print(f"Создание embeddings для {len(songs)} песен...")
        
        for idx, song in enumerate(songs):
            # Подготовка текста
            text = self._prepare_song_text(song)
            
            # Создание embedding
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text
                )
                
                embedding = response.data[0].embedding
                
                vectors.append({
                    "id": song.get("id", idx),
                    "embedding": embedding,
                    "metadata": song
                })
                
                if (idx + 1) % 10 == 0:
                    print(f"Обработано {idx + 1}/{len(songs)} песен...")
                    
            except Exception as e:
                print(f"Ошибка при обработке песни {song.get('title', 'Unknown')}: {e}")
                continue
        
        print(f"Успешно создано {len(vectors)} embeddings!")
        return vectors
    
    def build_index(self, vectors: List[Dict[str, Any]]) -> faiss.Index:
        """
        Создаёт FAISS индекс из векторов.
        
        Args:
            vectors: Список словарей с embeddings
            
        Returns:
            FAISS индекс
        """
        if not vectors:
            raise ValueError("Список векторов пуст!")
        
        # Создание индекса
        self.index = faiss.IndexFlatL2(self.dimension)
        
        # Подготовка массива embeddings
        embeddings_array = np.array([v["embedding"] for v in vectors]).astype("float32")
        
        # Добавление в индекс
        self.index.add(embeddings_array)
        
        # Сохранение метаданных
        self.vectors_metadata = vectors
        
        print(f"Индекс создан! Размер: {self.index.ntotal} векторов")
        return self.index
    
    def save_index(self, index_path: str, metadata_path: str):
        """
        Сохраняет индекс и метаданные на диск.
        
        Args:
            index_path: Путь для сохранения FAISS индекса
            metadata_path: Путь для сохранения метаданных
        """
        if self.index is None:
            raise ValueError("Индекс не создан! Сначала вызовите build_index()")
        
        # Сохранение индекса
        faiss.write_index(self.index, index_path)
        
        # Сохранение метаданных
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.vectors_metadata, f, ensure_ascii=False, indent=2)
        
        print(f"Индекс сохранён: {index_path}")
        print(f"Метаданные сохранены: {metadata_path}")
    
    def load_index(self, index_path: str, metadata_path: str):
        """
        Загружает индекс и метаданные с диска.
        
        Args:
            index_path: Путь к FAISS индексу
            metadata_path: Путь к метаданным
        """
        # Загрузка индекса
        self.index = faiss.read_index(index_path)
        
        # Загрузка метаданных
        with open(metadata_path, 'r', encoding='utf-8') as f:
            self.vectors_metadata = json.load(f)
        
        print(f"Индекс загружен: {self.index.ntotal} векторов")
    
    def get_query_embedding(self, query: str) -> np.ndarray:
        """
        Создаёт embedding для запроса пользователя.
        
        Args:
            query: Текст запроса
            
        Returns:
            NumPy массив с embedding
        """
        response = self.client.embeddings.create(
            model=self.model,
            input=query
        )
        
        return np.array([response.data[0].embedding]).astype("float32")

