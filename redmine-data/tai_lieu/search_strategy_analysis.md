# Hướng dẫn Tìm kiếm: Redmine Filter vs RAG Search

## Tổng quan

Hệ thống AI Redmine cung cấp **2 phương pháp tìm kiếm**:

1. **Redmine Filter**: Tìm kiếm chính xác dựa trên cấu trúc dữ liệu
2. **RAG Search**: Tìm kiếm ngữ nghĩa với AI, hiểu ngôn ngữ tự nhiên

---

## Khi nào sử dụng?

| Tình huống | Dùng | Ví dụ |
| --- | --- | --- |
| **Biết chính xác field/ID cần tìm** | Redmine Filter | `status_id=1`, `tracker_id=2`, `project_id=myproject` |
| **Cần kết quả ngay lập tức** | Redmine Filter | Tìm nhanh không cần AI processing |
| **Tìm theo từ khóa chính xác** | Redmine Filter | `"deploy production"`, `"API documentation"`, `issue_id=12345` |
| **Tìm theo thời gian** | Redmine Filter | `created_on=2024-01-01..2024-12-31`, `updated_on>=2024-01-01` |
| **Kết hợp nhiều điều kiện phức tạp** | Redmine Filter | `project_id=X, status_id=open, priority_id>=4` |
| **Không biết từ khóa chính xác** | RAG Search | Tìm theo ý tưởng/concept thay vì từ khóa cụ thể |
| **Muốn tìm theo ngữ nghĩa/ý tưởng** | RAG Search | `"Issue có lỗi về upload file?"`, `"Các issue liên quan đến vấn đề xử lý server lỗi?"` |
| **Hỏi bằng ngôn ngữ tự nhiên** | RAG Search | `"Hướng dẫn deploy RAG system"`, `"Có issue nào về performance của database không?"` |
| **Cần câu trả lời được tóm tắt** | RAG Search | Muốn có  tóm tắt, sources tự động |
| **Câu hỏi theo tính thống kê** ⚠️ *(Đang phát triển)* | RAG Search | `"Trong tháng có bao nhiêu bug?"`, `"Số lượng issue theo status"` |
| **Câu hỏi theo tính xu hướng** ⚠️ *(Đang phát triển)* | RAG Search | `"Bug loại này đang tăng hay giảm trong tháng này?"`, `"Xu hướng issue về performance"` |
| **Câu hỏi theo tính phân loại/phân tích** ⚠️ *(Đang phát triển)* | RAG Search | `"Bug chủ yếu rơi vào phân loại nào?"`, `"Phân tích nguyên nhân chính của các issue"` |

---

## Cách sử dụng hiệu quả

### Redmine Filter

#### Tips để dùng Redmine Filter hiệu quả

- Sử dụng khi bạn biết chính xác field và giá trị cần tìm
- Kết hợp nhiều điều kiện bằng dấu phẩy: `field1=value1, field2=value2`
- Dùng toán tử so sánh: `>=`, `<=`, `>`, `<`, `=`, `!=`
- Dùng khoảng thời gian: `created_on=2024-01-01..2024-12-31`
- Dùng `!*` để tìm giá trị null/empty

---

### RAG Search

#### Cách sử dụng

1. Vào trang **AI Search** trong Redmine UI
2. Nhập câu hỏi bằng ngôn ngữ tự nhiên vào search box
3. AI sẽ tự động:
   - Tìm các chunks liên quan bằng vector search
   - Generate answer dựa trên context
   - Trích xuất sources
   - Hiển thị answer + sources + chunks

#### Tips để dùng RAG Search hiệu quả

- Đặt câu hỏi rõ ràng, cụ thể: `"Issue nào về lỗi upload file?"` thay vì `"upload"`
- Sử dụng ngôn ngữ tự nhiên, không cần cú pháp đặc biệt
- Mô tả vấn đề/ý tưởng thay vì từ khóa: `"Vấn đề về performance"` thay vì `"performance"`
- Có thể hỏi câu hỏi phức tạp: `"Có issue nào về database performance và cách fix không?"`
- Kết quả sẽ có AI-generated answer kèm sources để bạn kiểm tra

---

## Quyết định nhanh

**Dùng Redmine Filter khi:**

- Biết chính xác field/ID/giá trị cần tìm
- Cần kết quả ngay lập tức
- Muốn tìm theo từ khóa chính xác
- Cần kết hợp nhiều điều kiện phức tạp

**Dùng RAG Search khi:**

- Không biết từ khóa chính xác
- Muốn tìm theo ngữ nghĩa/ý tưởng
- Hỏi bằng ngôn ngữ tự nhiên
- Cần câu trả lời được giải thích và tóm tắt
