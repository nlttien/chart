# Quy tắc hệ thống (Agent Rules)

## 1. Xác nhận trước khi thay đổi (Approval Required)
- KHÔNG tự ý chỉnh sửa code, file cấu hình hoặc thực hiện bất kỳ thay đổi nào trên hệ thống/codebase nếu chưa nhận được sự đồng ý/xác nhận từ người dùng.
- Luôn trình bày kế hoạch (plan) hoặc nội dung thay đổi dự kiến và chờ người dùng duyệt trước khi thực thi.

## 2. Quy trình Git & Deploy (Commit, Push, Pull Server)
- Mỗi khi có thay đổi được chấp thuận và hoàn thành:
  1. **Commit**: Gom nhóm thay đổi và tạo commit với thông điệp rõ ràng theo chuẩn Conventional Commits.
  2. **Push**: Push commit lên remote repository (GitHub).
  3. **Pull / Deploy**: Nếu dự án có server (Dev/Prod), thực hiện các bước pull / deploy tương ứng về server và kiểm tra lại trạng thái hoạt động.
- Khi xuất lệnh cho người dùng tự chạy (copy/paste): Luôn gộp đầy đủ cả 2 phần (Khối 1: Lệnh Commit & Push gộp cho tất cả repo liên quan; Khối 2: Lệnh Pull, Build & Deploy gộp đầy đủ cho Server).

## 3. Xử lý Trạng thái & Chuỗi Đa ngôn ngữ (Status & Multilingual Matching)
- Khi so sánh, lọc, hoặc đếm các giá trị trạng thái (Status, Role, Type, Category):
  - KHÔNG bao giờ so sánh khớp cứng duy nhất chuỗi tiếng Anh (như `status == 'Active'`).
  - LUÔN kiểm tra và hỗ trợ đa ngôn ngữ (Tiếng Việt & Tiếng Anh, viết hoa/viết thường), sử dụng so sánh từ khóa linh hoạt (VD: `cày`, `đang hoạt động`, `farming`, `active`, `ban`, `khóa`...) để tránh lỗi đếm sai hoặc không nhận diện được dữ liệu thực tế.

## 4. Quy tắc phản hồi ngắn gọn & Xử lý dữ liệu (Strict No-Boilerplate & Multi-Field Query)
- **TÍNH NGẮN GỌN & KHÔNG LẶP CÂU TRẢ LỜI RẬP KHUÔN (Strict No-Boilerplate Rule)**: TUYỆT ĐỐI KHÔNG lặp lại các câu trả lời rập khuôn mẫu. Khi người dùng hỏi hoặc muốn test/kiểm tra data, agent PHẢI trả lời trực tiếp vào trọng tâm câu hỏi, KHÔNG in lại khối lệnh Khối 2 hay nhắc lại hướng dẫn deploy trừ khi người dùng explicitly yêu cầu xuất lệnh.
- **XỬ LÝ DỮ LIỆU ĐA TRƯỜNG & KHÔNG KHỚP CỨNG (Case-Insensitive Multi-Field Query & Array Unwrapping)**: Khi tra cứu dữ liệu, KHÔNG bao giờ so sánh khớp cứng duy nhất 1 trường phân biệt hoa/thường (`name == account`). LUÔN tra cứu case-insensitive đa trường và giải bọc mảng ở FE.

## 5. Quy tắc Log Chuẩn mực & Cấu trúc Minh bạch (Smart Diagnostic & API Logging Rule)
- **TÍNH MINH BẠCH & KHÔNG NUỐT LỖI (No Silent Exception)**: TUYỆT ĐỐI KHÔNG nuốt ngoại lệ, KHÔNG trả về kết quả rỗng `[]` hoặc `status: success` ảo mà không có lý do/log giải thích chi tiết.
- **PHÂN LOẠI MÃ LỖI ĐỊNH DANH (Structured Error Codes)**: Tất cả ngoại lệ và sự kiện trong hệ thống (như cào dữ liệu, xử lý API, bypass WAF/Captcha, DOM selector) BẮT BUỘC phải được gán **Error Code chuẩn** (VD: `WAF_CAPTCHA_DETECTED`, `SLIDER_SOLVE_FAILED`, `DOM_ELEMENT_NOT_FOUND`, `HTTP_BLOCKED`, `TIMEOUT`, `COOKIES_EXPIRED`) kèm theo thông số ngữ cảnh chi tiết (`url`, `http_status`, `execution_time_ms`, `retry_count`).
- **HỖ TRỢ TRUY VẾT TỪ XA QUA REST API (Remote Log & Visual Debug API)**: Luôn xây dựng các endpoint kiểm tra log trực tiếp (`/api/v1/<platform>/logs`, `/api/v1/<platform>/status`, `/api/v1/<platform>/screenshot`) và cơ chế tự động chụp ảnh debug màn hình khi lỗi giao diện/Captcha để người dùng kiểm tra ngay trên API Postman/Browser mà không bao giờ bị rơi vào tình trạng "không biết lỗi ở đâu".
