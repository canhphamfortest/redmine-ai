"""Handler endpoint các issues liên quan"""
import time
import asyncio
import logging
import re
import numpy as np
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db, SessionLocal
from app.models import Source, Chunk, Embedding
from app.services.retriever import retriever

logger = logging.getLogger(__name__)


async def find_related_issues(
    issue_id: int,
    top_k: Optional[int] = 20,
    db: Session = Depends(get_db)
):
    """Tìm các issues liên quan bằng cách sử dụng vector embedding của issue đã cho.
    
    Endpoint này tìm các Redmine issues liên quan đến một issue cụ thể bằng cách:
    1. Lấy issue source, chunks, và embeddings từ database
    2. Search với từng embedding riêng (mỗi chunk có thể đại diện một khía cạnh khác nhau)
    3. Merge kết quả từ tất cả searches, giữ similarity score cao nhất cho mỗi chunk
    4. Nhóm chunks theo issue và lấy top issues dựa trên similarity scores
    5. Trả về danh sách các issues liên quan với similarity scores
    
    Args:
        issue_id: Redmine issue ID cần tìm issues liên quan (int)
        top_k: Số lượng issues tối đa trả về (mặc định: 20)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - issue_id: ID của issue gốc (int)
            - related_issues: Danh sách issues liên quan (List[Dict]):
                - issue_id: ID của issue liên quan (int)
                - similarity_score: Điểm similarity (float, 0-1)
                - similarity_percentage: Điểm similarity dạng phần trăm (float)
                - subject: Subject của issue nếu có (str, optional)
            - count: Số lượng issues liên quan (int)
            - response_time_ms: Thời gian xử lý tính bằng milliseconds (int)
    
    Raises:
        HTTPException: 
            - HTTP 404 nếu issue không tồn tại trong database
            - HTTP 404 nếu không có chunks hoặc embeddings cho issue
            - HTTP 500 nếu có lỗi trong quá trình tìm kiếm
    
    Note:
        - Search với từng embedding riêng và merge kết quả
        - Mỗi chunk có thể đại diện cho một khía cạnh khác nhau của issue
        - Merge giữ similarity score cao nhất cho mỗi chunk
        - Loại trừ issue hiện tại khỏi kết quả
        - Chọn top issues dựa trên similarity scores (không dùng AI)
        - Tối đa top_k issues liên quan được trả về
    """
    start_time = time.time()
    
    try:
        # Bước 1: Tìm source cho issue này
        external_id = f"redmine_issue_{issue_id}"
        source = db.query(Source).filter(
            Source.source_type == 'redmine_issue',
            Source.external_id == external_id
        ).first()
        
        if not source:
            raise HTTPException(
                status_code=404,
                detail=f"Issue {issue_id} not found in database. Please sync the issue first."
            )
        
        logger.info(f"Found source for issue {issue_id}: {source.id}")
        
        # Bước 2: Lấy chunks và embeddings cho issue này
        # Lấy issue_metadata và issue_description (tất cả)
        base_chunks = db.query(Chunk).filter(
            Chunk.source_id == source.id,
            Chunk.status == 'processed',
            Chunk.chunk_type.in_(['issue_metadata', 'issue_description'])
        ).all()

        # Lấy 4 issue_comment mới nhất (theo ordinal giảm dần)
        comment_chunks = db.query(Chunk).filter(
            Chunk.source_id == source.id,
            Chunk.status == 'processed',
            Chunk.chunk_type == 'issue_comment'
        ).order_by(Chunk.ordinal.desc()).limit(4).all()

        chunks = base_chunks + comment_chunks
        logger.info(f"Issue {issue_id}: {len(base_chunks)} base chunks (metadata+description), {len(comment_chunks)} comment chunks (latest 4)")
        
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail=f"No processed chunks found for issue {issue_id}"
            )
        
        # Lấy embeddings cho các chunks này
        chunk_ids = [chunk.id for chunk in chunks]
        embeddings = db.query(Embedding).filter(
            Embedding.chunk_id.in_(chunk_ids),
            Embedding.status == 'active'
        ).all()
        
        if not embeddings:
            raise HTTPException(
                status_code=404,
                detail=f"No active embeddings found for issue {issue_id}"
            )
        
        logger.info(f"Found {len(embeddings)} embeddings for issue {issue_id}")
        
        # Bước 3: Search với từng embedding song song và merge kết quả
        # Lý do: Mỗi chunk có thể đại diện cho một khía cạnh khác nhau của issue
        # Chạy song song (asyncio.gather + run_in_executor) để giảm thời gian chờ
        all_similar_chunks = {}
        loop = asyncio.get_running_loop()
        exclude_ids = [str(source.id)]

        def _search_one(emb_raw, idx):
            """Chạy search_by_embedding trong thread pool với session riêng (thread-safe)."""
            if hasattr(emb_raw, 'tolist'):
                emb_list = emb_raw.tolist()
            elif isinstance(emb_raw, list):
                emb_list = emb_raw
            else:
                emb_list = np.array(emb_raw).tolist()

            # Tạo session riêng cho mỗi thread để tránh race condition
            thread_db = SessionLocal()
            try:
                result = retriever.search_by_embedding(
                    embedding_vector=emb_list,
                    db=thread_db,
                    top_k=top_k * 2,  # Lấy nhiều ứng viên từ mỗi embedding
                    exclude_source_ids=exclude_ids  # Loại trừ issue hiện tại
                )
                logger.debug(f"Search with embedding {idx+1}/{len(embeddings)}: found {len(result)} chunks")
                return result
            finally:
                thread_db.close()

        # Chạy tất cả embedding searches song song
        tasks = [
            loop.run_in_executor(None, _search_one, embedding.embedding, idx)
            for idx, embedding in enumerate(embeddings)
        ]
        search_results = await asyncio.gather(*tasks)

        # Merge kết quả từ tất cả searches, giữ similarity score cao nhất cho mỗi chunk
        for chunks in search_results:
            for chunk in chunks:
                chunk_id = chunk.get('chunk_id') or chunk.get('metadata', {}).get('chunk_id')
                if chunk_id:
                    if chunk_id not in all_similar_chunks or \
                       chunk['similarity_score'] > all_similar_chunks[chunk_id]['similarity_score']:
                        all_similar_chunks[chunk_id] = chunk
                else:
                    # Nếu không có chunk_id, dùng text + source_reference làm key
                    key = f"{chunk.get('text', '')[:50]}_{chunk.get('metadata', {}).get('source_reference', '')}"
                    if key not in all_similar_chunks or \
                       chunk['similarity_score'] > all_similar_chunks[key]['similarity_score']:
                        all_similar_chunks[key] = chunk
        
        # Chuyển dict về list và sắp xếp theo similarity score
        similar_chunks = list(all_similar_chunks.values())
        similar_chunks.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        logger.info(f"Found {len(similar_chunks)} unique similar chunks after merging {len(embeddings)} searches")
        
        if not similar_chunks:
            logger.warning(f"No similar chunks found for issue {issue_id}")
            return {
                "issue_id": issue_id,
                "related_issues": [],
                "count": 0,
                "response_time_ms": int((time.time() - start_time) * 1000)
            }
        
        # Bước 5: Nhóm chunks theo source (issue) và lấy issue IDs
        # Trích xuất issue IDs từ source_reference (định dạng: "redmine_issue_308")
        issue_candidates = {}
        for chunk in similar_chunks:
            source_ref = chunk.get('metadata', {}).get('source_reference', '')
            heading = chunk.get('metadata', {}).get('heading', '')
            chunk_text = chunk.get('text', '')
            
            logger.debug(f"Processing chunk: source_ref={source_ref}, heading={heading}, similarity={chunk.get('similarity_score', 0)}")
            
            if source_ref and source_ref.startswith('redmine_issue_'):
                try:
                    candidate_issue_id = int(source_ref.replace('redmine_issue_', ''))
                    if candidate_issue_id != issue_id:
                        # Giữ điểm similarity cao nhất cho mỗi issue
                        if candidate_issue_id not in issue_candidates or \
                           chunk['similarity_score'] > issue_candidates[candidate_issue_id]['similarity_score']:
                            # Thử trích xuất subject từ heading hoặc chunk text
                            subject = heading if heading else None
                            if not subject and chunk_text:
                                # Thử trích xuất từ chunk text (định dạng: "Issue #123: Subject")
                                match = re.search(r'Issue\s*#?\d+:\s*(.+?)(?:\n|$)', chunk_text)
                                if match:
                                    subject = match.group(1).strip()
                            
                            issue_candidates[candidate_issue_id] = {
                                'issue_id': candidate_issue_id,
                                'similarity_score': chunk['similarity_score'],
                                'source_id': chunk.get('metadata', {}).get('source_id'),
                                'subject': subject,  # Thử lấy subject từ metadata
                                'heading': heading
                            }
                            logger.debug(f"Added candidate issue {candidate_issue_id}: subject={subject}, similarity={chunk['similarity_score']}")
                except ValueError as ve:
                    logger.warning(f"Could not parse issue ID from source_reference: {source_ref}, error: {ve}")
                    continue
            else:
                logger.debug(f"Skipping chunk with invalid source_reference: {source_ref}")
        
        logger.info(f"Found {len(issue_candidates)} candidate issues: {list(issue_candidates.keys())}")
        
        # Bước 6: Chọn top issues dựa trên similarity scores (không dùng AI)
        # Sắp xếp theo similarity score giảm dần và lấy top_k
        sorted_candidates = sorted(
            issue_candidates.items(), 
            key=lambda x: x[1]['similarity_score'], 
            reverse=True
        )[:top_k]
        
        related_issue_ids = [candidate_id for candidate_id, _ in sorted_candidates]
        logger.info(f"Selected {len(related_issue_ids)} related issues based on similarity scores: {related_issue_ids}")
        
        # Bước 7: Xây dựng response với chi tiết issue
        related_issues = []
        for related_issue_id in related_issue_ids:
            if related_issue_id in issue_candidates:
                candidate_data = issue_candidates[related_issue_id]
                issue_data = {
                    'issue_id': related_issue_id,
                    'similarity_score': candidate_data['similarity_score'],
                    'similarity_percentage': round(candidate_data['similarity_score'] * 100, 1)
                }
                
                # Thêm subject nếu có từ chunk metadata
                if candidate_data.get('subject'):
                    issue_data['subject'] = candidate_data['subject']
                    logger.debug(f"Including subject for issue {related_issue_id}: {candidate_data['subject']}")
                else:
                    logger.warning(f"No subject found for issue {related_issue_id} in chunk metadata")
                
                related_issues.append(issue_data)
        
        # Sắp xếp theo điểm similarity giảm dần (cao nhất trước)
        related_issues.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        response_time = int((time.time() - start_time) * 1000)
        
        logger.info(f"Returning {len(related_issues)} related issues for issue {issue_id}, response_time: {response_time}ms")
        
        return {
            "issue_id": issue_id,
            "related_issues": related_issues,
            "count": len(related_issues),
            "response_time_ms": response_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to find related issues for issue {issue_id}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {repr(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

