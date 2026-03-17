module CustomFeatures
  module Formatters
    # Formatter cho kết quả tìm kiếm từ RAG search
    # Chuyển đổi raw response từ AI service thành format chuẩn
    class SearchResultFormatter
      # Chuẩn hóa chunks từ RAG search response
      # Chuyển đổi raw chunks thành format thống nhất với metadata
      #
      # @param raw_chunks [Array<Hash>, nil] Mảng các chunks từ RAG response
      # @return [Array<Hash>] Mảng các chunks đã được normalize, mỗi chunk chứa:
      #   - id: Chunk ID (hoặc chunk_id)
      #   - chunk_type: Loại chunk (issue, note, etc.)
      #   - text: Nội dung text của chunk
      #   - similarity: Similarity score
      #   - distance: Distance score
      #   - metadata: Hash metadata đã được normalize
      def self.normalize_chunks(raw_chunks)
        Array.wrap(raw_chunks).map do |chunk|
          data = chunk.with_indifferent_access
          metadata = normalize_metadata(data[:metadata])

          {
            id: data[:chunk_id] || data[:id],
            chunk_type: data[:chunk_type],
            text: data[:text],
            similarity: data[:similarity_score],
            distance: data[:distance],
            metadata: metadata
          }
        end
      end

      # Format sources từ RAG response
      # Chuyển đổi sources thành format với indifferent access (symbol/string keys)
      #
      # @param sources [Array<Hash>, nil] Mảng các sources từ RAG response
      # @return [Array<Hash>] Mảng các sources đã được format với indifferent access
      def self.format_sources(sources)
        Array.wrap(sources).map do |source|
          source.with_indifferent_access
        end
      end

      private

      # Chuẩn hóa metadata thành Hash với indifferent access
      # Đảm bảo metadata luôn là Hash, không phải nil hoặc kiểu khác
      #
      # @param metadata [Hash, nil, Object] Metadata object
      # @return [Hash] Hash metadata với indifferent access, hoặc {} nếu không hợp lệ
      def self.normalize_metadata(metadata)
        return {} unless metadata

        metadata.is_a?(Hash) ? metadata.with_indifferent_access : {}
      end
    end
  end
end

