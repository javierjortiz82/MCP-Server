from google import genai
from google.genai import types

from config import settings
from utils.logger import setup_logging

# Setup logger for embeddings
logger = setup_logging("mcp_embeddings")


class EmbeddingsClient:
    """Client for generating text embeddings using Google Gemini AI.

    This client provides a simple interface to generate vector embeddings from text
    using Google's Gemini embedding model. The embeddings are used for semantic
    search and similarity calculations in the product search system.

    Attributes:
        _client: Google GenAI client instance
        _model: Name of the embedding model to use (default: gemini-embedding-001)

    Example:
        >>> client = EmbeddingsClient()
        >>> vectors = client.embed(["laptop gaming", "silla oficina"])
        >>> len(vectors)  # 2 vectors
        2
        >>> len(vectors[0])  # 1536 dimensions
        1536
    """

    def __init__(self) -> None:
        """Initialize the embeddings client with Google Gemini API.

        Reads API key and model configuration from settings and creates
        a Google GenAI client instance.

        Raises:
            ValueError: If GOOGLE_API_KEY is not set in settings
        """
        logger.info(
            "Inicializando cliente de embeddings con modelo: %s",
            settings.EMBEDDING_MODEL,
        )
        self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        self._model = settings.EMBEDDING_MODEL

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Converts each text into a 1536-dimensional vector using Google's Gemini
        embedding model. These vectors capture semantic meaning and enable
        similarity-based search operations.

        Args:
            texts: List of text strings to convert into embeddings

        Returns:
            List of embedding vectors, where each vector is a list of 1536 floats.
            Empty list if input is empty or if embeddings generation fails.

        Raises:
            Exception: If API call fails or authentication error occurs

        Example:
            >>> embeddings = client.embed(["robot aspirador", "laptop gaming"])
            >>> len(embeddings)
            2
            >>> isinstance(embeddings[0], list)
            True
            >>> len(embeddings[0])  # Gemini embedding-001 dimension
            1536

        Note:
            - Each API call counts toward your Google API quota
            - Batch processing is more efficient than individual calls
            - Model: gemini-embedding-001 (supports Spanish and English)
        """
        if not texts:
            logger.debug("Lista de textos vacía, retornando lista vacía")
            return []

        logger.debug("Generando embeddings para %d textos", len(texts))
        try:
            # Usar la API correcta de Google GenAI 2025
            resp = self._client.models.embed_content(
                model=self._model,
                contents=texts,
                config=types.EmbedContentConfig(output_dimensionality=1536),
            )
            # Extraer embeddings de la respuesta
            if resp.embeddings is None:
                logger.warning("Respuesta sin embeddings")
                return []
            vectors: list[list[float]] = [
                list(embedding.values) for embedding in resp.embeddings if embedding.values
            ]
            logger.debug("Embeddings generados exitosamente: %d vectores", len(vectors))
            return vectors
        except Exception as e:
            logger.error("Error al generar embeddings: %s", e)
            raise


emb_client = EmbeddingsClient()
