"""Lớp RAG chain chính"""
import logging
import time
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session

from app.config import settings
from app.services.retriever import retriever
from app.services.cache import cache
from app.services.openai_usage_tracker import OpenAIUsageTracker
from app.services.rag_chain.generator import is_error_response
from app.services.llm_provider import get_provider
from app.services.openai_config_service import LLMConfigService
from app.services.rag_chain.context_builder import build_context, create_prompt
from app.services.rag_chain.source_extractor import extract_sources

logger = logging.getLogger(__name__)


class RAGChain:
    """RAG (Retrieval-Augmented Generation) chain sử dụng OpenAI.
    
    Class này thực hiện RAG pipeline hoàn chỉnh:
    1. Retrieve: Tìm kiếm chunks liên quan bằng vector similarity
    2. Augment: Xây dựng context từ chunks
    3. Generate: Tạo câu trả lời bằng OpenAI API
    
    Hỗ trợ caching để cải thiện performance và giảm chi phí API.
    
    Attributes:
        _client: OpenAI client instance (lazy initialized)
        _model: Tên model OpenAI được sử dụng (lazy initialized)
        _initialized: Flag đánh dấu đã khởi tạo chưa (bool)
    """
    
    def __init__(self):
        """Khởi tạo RAGChain với lazy initialization."""
        self._client = None
        self._model = None
        self._provider_name = None
        self._provider = None
        self._initialized = False
    
    def _ensure_initialized(self, force_reload: bool = False):
        """Khởi tạo lazy - chỉ khởi tạo khi thực sự cần.
        
        Hàm này khởi tạo OpenAI client và model name chỉ khi được gọi lần đầu.
        Model được lấy từ database config (nếu có), fallback về settings.
        
        Args:
            force_reload: Nếu True, reload config từ DB ngay cả khi đã initialized (bool)
        
        Raises:
            ValueError: Nếu OpenAI API key chưa được cấu hình
        
        Note:
            - Client được tạo với max_retries=0 để fail nhanh khi có lỗi
            - Model được lấy từ OpenAIConfigService.get_default_provider_and_model()
            - Nếu không có trong DB, sử dụng settings.openai_model
            - Nếu force_reload=True, sẽ reload config từ DB để đảm bảo dùng model mới nhất
        """
        # Nếu đã initialized và không force reload, kiểm tra xem có cần reload không
        if self._initialized and not force_reload:
            # Kiểm tra xem default model có thay đổi không
            provider_info = LLMConfigService.get_default_provider_and_model()
            new_provider = provider_info.get("provider") or settings.default_llm_provider or "openai"
            new_model = provider_info.get("model") or settings.openai_model
            
            # Nếu model hoặc provider thay đổi, cần reload
            if new_model != self._model or new_provider != self._provider_name:
                force_reload = True
            else:
                return
        
        # Reload config từ DB để đảm bảo dùng model mới nhất
        provider_info = LLMConfigService.get_default_provider_and_model()
        self._provider_name = provider_info.get("provider") or settings.default_llm_provider or "openai"
        self._model = provider_info.get("model") or settings.openai_model
        api_key = provider_info.get("api_key")
        base_url = provider_info.get("base_url")

        # Build provider + client
        self._provider = get_provider(
            provider_name=self._provider_name,
            model=self._model,
            api_key=api_key,
            base_url=base_url,
        )
        self._client = self._provider.get_client()
        
        self._initialized = True
    
    @property
    def client(self):
        """Lấy OpenAI client (lazy initialization).
        
        Returns:
            OpenAI: OpenAI client instance
        
        Note:
            - Khởi tạo client nếu chưa được khởi tạo
            - Client được tái sử dụng sau khi khởi tạo
        """
        self._ensure_initialized()
        return self._client
    
    @property
    def model(self):
        """Lấy tên model (lazy initialization).
        
        Returns:
            str: Tên model OpenAI được sử dụng
        
        Note:
            - Khởi tạo model nếu chưa được khởi tạo
            - Model được lấy từ database config hoặc settings
        """
        self._ensure_initialized()
        return self._model

    @property
    def provider_name(self):
        self._ensure_initialized()
        return self._provider_name
    
    def generate_answer(
        self,
        query: str,
        db: Session,
        use_cache: bool = True,
        skip_retrieval: bool = False,
        project_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Tạo câu trả lời sử dụng RAG với timing breakdown.
        
        Returns thêm 'timing_breakdown' dict với thời gian từng phần.
        """
        """Tạo câu trả lời sử dụng RAG với tùy chọn caching.
        
        Quy trình RAG:
        1. Kiểm tra cache (nếu use_cache=True)
        2. Retrieve chunks liên quan (nếu skip_retrieval=False)
        3. Build context và prompt
        4. Generate answer bằng OpenAI API
        5. Log usage và cache response
        
        Args:
            query: Query của người dùng hoặc prompt đầy đủ (string).
                   Nếu skip_retrieval=True, query được sử dụng trực tiếp làm prompt
            db: Database session
            use_cache: Có sử dụng Redis cache cho response không (mặc định: True).
                     Nếu True, kiểm tra cache trước và lưu response sau khi generate
            skip_retrieval: Nếu True, bỏ qua retrieval và sử dụng query trực tiếp làm prompt
                           (mặc định: False). Hữu ích khi đã có prompt đầy đủ
        
        Returns:
            Dict[str, Any]: Dictionary chứa:
                - answer: Câu trả lời được tạo bởi AI (str)
                - sources: Danh sách sources được trích xuất từ chunks (List[Dict])
                - retrieved_chunks: Danh sách chunks đã retrieve (List[Dict])
                - cached: True nếu response từ cache, False nếu không (bool)
                - usage: Thông tin usage (input_token, output_token, total_tokens) (Dict, optional)
                - usage_log_id: ID của LLMUsageLog entry (UUID, optional, chỉ có khi có AI call)
                - generation_time_ms: Thời gian generation AI tính bằng milliseconds (int, optional)
        
        Note:
            - Response được cache trong Redis với TTL 1 ngày (86400 giây)
            - Empty responses được cache với TTL ngắn hơn (1 giờ)
            - Error responses không được cache
            - Usage được log vào database cho tracking và billing
        """
        try:
            timing_breakdown = {}
            
            # Kiểm tra cache trước
            cache_check_start = time.time()
            cached_response = self._check_cache(query, db, use_cache)
            timing_breakdown['cache_check_ms'] = int((time.time() - cache_check_start) * 1000)
            
            if cached_response:
                cached_response['timing_breakdown'] = timing_breakdown
                return cached_response
            
            # Lấy chunks và xây dựng prompt
            retrieval_start = time.time()
            chunks, prompt = self._retrieve_chunks_and_build_prompt(
                query, db, skip_retrieval, use_cache, timing_breakdown, project_ids
            )
            timing_breakdown['retrieval_total_ms'] = int((time.time() - retrieval_start) * 1000)
            
            if chunks is None:  # Response rỗng đã được trả về
                empty_response = self._build_empty_response(query, use_cache)
                empty_response['timing_breakdown'] = timing_breakdown
                return empty_response
            
            # Tạo câu trả lời với OpenAI
            llm_start = time.time()
            answer, usage_info, generation_time_ms = self._generate_with_openai(prompt)
            timing_breakdown['llm_generation_ms'] = generation_time_ms
            timing_breakdown['llm_total_ms'] = int((time.time() - llm_start) * 1000)
            
            # Ghi log usage và lấy usage_log_id
            log_start = time.time()
            usage_log_id = self._log_usage(query, prompt, answer, usage_info, generation_time_ms, db)
            timing_breakdown['usage_log_ms'] = int((time.time() - log_start) * 1000)
            
            # Xây dựng và cache response
            build_start = time.time()
            response = self._build_response(answer, chunks, usage_info, usage_log_id, generation_time_ms, timing_breakdown)
            timing_breakdown['build_response_ms'] = int((time.time() - build_start) * 1000)
            
            cache_write_start = time.time()
            self._cache_response_if_needed(query, response, answer, usage_info, use_cache)
            timing_breakdown['cache_write_ms'] = int((time.time() - cache_write_start) * 1000)
            
            response['timing_breakdown'] = timing_breakdown
            return response
            
        except Exception as e:
            return self._handle_generation_error(e)
    
    def _check_cache(self, query: str, db: Session, use_cache: bool) -> Optional[Dict[str, Any]]:
        """Kiểm tra cache cho response hiện có.
        
        Hàm này query Redis cache để tìm response đã được cache cho query.
        Nếu tìm thấy, log cached usage (0 tokens) và trả về response.
        
        Args:
            query: Query của người dùng (string)
            db: Database session để log cached usage
            use_cache: Flag có sử dụng cache không (bool)
        
        Returns:
            Dict[str, Any] | None: Response đã cache nếu tìm thấy, None nếu không
        
        Note:
            - Chỉ kiểm tra cache nếu use_cache=True
            - Cached response được đánh dấu cached=True
            - Log cached usage với 0 tokens để tracking
        """
        if not use_cache:
            return None
        
        cached_response = cache.get_rag_response(query)
        if not cached_response:
            return None
        
        logger.info(f"Returning cached response for query: {query[:50]}...")
        cached_response['cached'] = True
        
        # Ghi log cached usage (không có API call)
        try:
            usage_log = OpenAIUsageTracker.log_usage(
                model=self.model,
                input_token=0,
                output_token=0,
                total_tokens=0,
                user_query=query,
                cached=True,
                response_time_ms=0,
                metadata=None,
                db=db,
                provider=self.provider_name,
            )
            # Thêm usage_log_id và generation_time_ms vào cached response
            cached_response['usage_log_id'] = usage_log.id
            cached_response['generation_time_ms'] = 0  # Cached nên không có generation time
        except Exception as log_error:
            logger.warning(f"Failed to log cached usage: {log_error}")
        
        return cached_response
    
    def _retrieve_chunks_and_build_prompt(
        self,
        query: str,
        db: Session,
        skip_retrieval: bool,
        use_cache: bool,
        timing_breakdown: Dict[str, Any],
        project_ids: Optional[List[int]] = None
    ) -> Tuple[Optional[List[Dict[str, Any]]], str]:
        """Lấy chunks và xây dựng prompt.
        
        Hàm này thực hiện retrieval và prompt building:
        - Nếu skip_retrieval=True: Trả về empty chunks và query làm prompt
        - Nếu skip_retrieval=False: Retrieve chunks, build context, tạo prompt
        
        Args:
            query: Query của người dùng (string)
            db: Database session
            skip_retrieval: Có bỏ qua retrieval không (bool)
            use_cache: Flag có sử dụng cache không (bool, không được sử dụng trong hàm này)
        
        Returns:
            Tuple[Optional[List[Dict]], str]: Tuple chứa:
                - chunks: Danh sách chunks đã retrieve, hoặc [] nếu skip_retrieval,
                         hoặc None nếu không tìm thấy chunks (cần trả về empty response)
                - prompt: Prompt đầy đủ để gửi đến OpenAI
        
        Note:
            - Sử dụng retriever.search() để lấy chunks tốt nhất
            - Context được build từ chunks với ưu tiên issue_metadata
            - Prompt được tạo bằng create_prompt() với instructions và context
        """
        if skip_retrieval:
            return [], query
        
        # Lấy các chunks liên quan bằng vector search
        # Note: vector_search bao gồm cả embedding generation và SQL query
        vector_search_start = time.time()
        chunks = retriever.search(
            query=query,
            db=db,
            project_ids=project_ids
        )
        vector_search_total_ms = int((time.time() - vector_search_start) * 1000)
        timing_breakdown['vector_search_ms'] = vector_search_total_ms
        # Embedding generation time sẽ được log trong vector_search module
        
        if not chunks:
            return None, ""  # Báo hiệu response rỗng
        
        # Xây dựng context từ chunks (ưu tiên issue_metadata)
        context_start = time.time()
        context = build_context(chunks)
        timing_breakdown['context_build_ms'] = int((time.time() - context_start) * 1000)
        
        # Tạo prompt
        prompt_start = time.time()
        prompt = create_prompt(query, context)
        timing_breakdown['prompt_build_ms'] = int((time.time() - prompt_start) * 1000)
        
        return chunks, prompt
    
    def _build_empty_response(self, query: str, use_cache: bool) -> Dict[str, Any]:
        """Xây dựng response rỗng khi không tìm thấy chunks.
        
        Hàm này tạo response khi không có chunks liên quan được tìm thấy.
        Response rỗng vẫn được cache để tránh query lại nhiều lần.
        
        Args:
            query: Query của người dùng (string)
            use_cache: Có cache response rỗng không (bool)
        
        Returns:
            Dict[str, Any]: Dictionary response rỗng:
                - answer: Thông báo không tìm thấy thông tin (str)
                - sources: Danh sách rỗng (List)
                - retrieved_chunks: Danh sách rỗng (List)
                - cached: False (bool)
        
        Note:
            - Response rỗng được cache với TTL ngắn hơn (1 giờ) so với response bình thường
            - Giúp tránh query lại nhiều lần cho các query không có kết quả
        """
        response = {
            'answer': "Tôi không tìm thấy thông tin liên quan trong cơ sở dữ liệu. Vui lòng thử câu hỏi khác.",
            'sources': [],
            'retrieved_chunks': [],
            'cached': False
        }
        
        # Cache cả response rỗng (có thể dùng TTL ngắn hơn)
        if use_cache:
            cache.set_rag_response(query, response, ttl_seconds=3600)  # 1 hour for empty results
        
        return response
    
    def _generate_with_openai(self, prompt: str) -> Tuple[str, Dict[str, Any], int]:
        """Generate bằng provider abstraction (giữ tên hàm để tương thích)."""
        # Đảm bảo provider đã được khởi tạo và kiểm tra xem có cần reload config không
        # Logic trong _ensure_initialized sẽ tự động reload nếu model thay đổi
        self._ensure_initialized()
        
        if self._provider is None:
            raise ValueError("LLM provider is not initialized. Please check your API key configuration.")
        
        generation_start = time.time()
        answer, usage_info = self._provider.generate(prompt)
        generation_time_ms = int((time.time() - generation_start) * 1000)
        return answer, usage_info, generation_time_ms
    
    def _log_usage(
        self,
        query: str,
        prompt: str,
        answer: str,
        usage_info: Dict[str, Any],
        generation_time_ms: int,
        db: Session
    ) -> Optional[Any]:
        """Ghi log OpenAI usage và chi tiết vào database.
        
        Hàm này log usage information và prompt/response details vào database
        để tracking và billing. Lỗi logging không làm gián đoạn quá trình generate.
        
        Args:
            query: Query gốc của người dùng (string)
            prompt: Prompt đầy đủ đã gửi đến OpenAI (string)
            answer: Câu trả lời từ OpenAI (string)
            usage_info: Thông tin usage từ OpenAI API (Dict)
            generation_time_ms: Thời gian generation tính bằng milliseconds (int)
            db: Database session
        
        Returns:
            UUID | None: ID của LLMUsageLog entry đã tạo, hoặc None nếu có lỗi
        
        Note:
            - Log usage vào OpenAIUsageLog table
            - Log chi tiết (prompt, response) vào OpenAIUsageLogDetail table
            - Lỗi logging được catch và log warning, không raise exception
            - Usage được sử dụng để tính chi phí và thống kê
        """
        try:
            usage_log = OpenAIUsageTracker.log_usage(
                model=self.model,
                input_token=usage_info.get('input_token', 0),
                output_token=usage_info.get('output_token', 0),
                total_tokens=usage_info.get('total_tokens', 0),
                prompt_token=usage_info.get('prompt_token', 0),
                user_query=query,
                cached=False,
                response_time_ms=generation_time_ms,
                metadata=None,
                db=db,
                provider=self.provider_name,
            )
            
                # Ghi log chi tiết prompt và response
            try:
                OpenAIUsageTracker.log_usage_detail(
                    usage_log_id=usage_log.id,
                    prompt=prompt,
                    response=answer,
                    db=db
                )
            except Exception as detail_error:
                logger.warning(f"Failed to log OpenAI usage detail: {detail_error}")
            
            return usage_log.id
        except Exception as log_error:
            logger.warning(f"Failed to log OpenAI usage: {log_error}")
            return None
    
    def _build_response(
        self,
        answer: str,
        chunks: List[Dict[str, Any]],
        usage_info: Dict[str, Any],
        usage_log_id: Optional[Any] = None,
        generation_time_ms: Optional[int] = None,
        timing_breakdown: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Xây dựng dictionary response từ answer và chunks.
        
        Hàm này tổng hợp answer, sources, và chunks thành response dictionary
        hoàn chỉnh để trả về cho client.
        
        Args:
            answer: Câu trả lời được tạo bởi AI (string)
            chunks: Danh sách chunks đã retrieve (List[Dict])
            usage_info: Thông tin usage từ OpenAI API (Dict)
            usage_log_id: ID của LLMUsageLog entry (UUID, optional)
            generation_time_ms: Thời gian generation tính bằng milliseconds (int, optional)
        
        Returns:
            Dict[str, Any]: Dictionary response hoàn chỉnh:
                - answer: Câu trả lời (str)
                - sources: Danh sách sources được extract từ chunks (List[Dict])
                - retrieved_chunks: Danh sách chunks đã retrieve (List[Dict])
                - cached: False (bool)
                - usage: Thông tin usage (Dict)
                - usage_log_id: ID của LLMUsageLog entry (UUID, optional)
                - generation_time_ms: Thời gian generation tính bằng milliseconds (int, optional)
        
        Note:
            - Sources được extract bằng extract_sources() từ chunks
            - Mỗi source chứa title, type, url, project
        """
        # Extract sources với timing
        source_extract_start = time.time()
        sources = extract_sources(chunks)
        if timing_breakdown is not None:
            timing_breakdown['source_extract_ms'] = int((time.time() - source_extract_start) * 1000)
        
        response = {
            'answer': answer,
            'sources': sources,
            'retrieved_chunks': chunks,
            'cached': False,
            'usage': usage_info
        }
        
        # Thêm usage_log_id và generation_time_ms nếu có
        if usage_log_id is not None:
            response['usage_log_id'] = usage_log_id
        if generation_time_ms is not None:
            response['generation_time_ms'] = generation_time_ms
        
        return response
    
    def _cache_response_if_needed(
        self,
        query: str,
        response: Dict[str, Any],
        answer: str,
        usage_info: Dict[str, Any],
        use_cache: bool
    ) -> None:
        """Cache response nếu thành công và caching được bật.
        
        Hàm này kiểm tra xem response có nên được cache không:
        - Chỉ cache nếu use_cache=True
        - Không cache error responses (được phát hiện bằng is_error_response)
        - Cache với TTL 1 ngày (86400 giây)
        
        Args:
            query: Query của người dùng (string)
            response: Response dictionary đã build (Dict)
            answer: Câu trả lời từ AI (string)
            usage_info: Thông tin usage từ OpenAI API (Dict)
            use_cache: Có cache response không (bool)
        
        Note:
            - Error responses không được cache để tránh cache các lỗi tạm thời
            - Success responses được cache để cải thiện performance
            - Cache key được generate từ query (normalized và hashed)
        """
        if not use_cache:
            return
        
        if is_error_response(answer, usage_info):
            logger.info(f"Not caching error response for query: {query[:50]}...")
        else:
            cache.set_rag_response(query, response, ttl_seconds=86400)
            logger.debug(f"Cached successful response for query: {query[:50]}...")
    
    def _handle_generation_error(self, error: Exception) -> Dict[str, Any]:
        """Xử lý lỗi generation và trả về error response.
        
        Hàm này catch exception trong quá trình generate và trả về error response
        thân thiện với người dùng. Error response không được cache.
        
        Args:
            error: Exception đã xảy ra (Exception)
        
        Returns:
            Dict[str, Any]: Dictionary error response:
                - answer: Thông báo lỗi thân thiện (str)
                - sources: Danh sách rỗng (List)
                - retrieved_chunks: Danh sách rỗng (List)
                - cached: False (bool)
        
        Note:
            - Error được log trước khi trả về response
            - Error message được include trong answer để user biết
            - Error response không được cache
        """
        logger.error(f"RAG generation failed: {error}")
        return {
            'answer': f"Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi: {str(error)}",
            'sources': [],
            'retrieved_chunks': [],
            'cached': False
        }

