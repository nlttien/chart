# Autonomous Engineering Agent System (AGENTS.md)

> Inspired by the `reverse-skill` framework (AI-powered routing + On-demand toolchain + Self-evolving knowledge base + Unified Project Governance)

Welcome to the **Unified Agent System** across `D:\codecuatien`. This system equips AI agents with deterministic routing, verified playbooks, game memory reverse engineering knowledge, web/chart visualization standards, and an evolving bug-fix registry for developing, debugging, and maintaining all projects (`ExileApi-Compiled`, `autobuypoe`, `chart`, etc.).

---

## 🎯 Core Operating Principles & Governance Rules

### 1. 📋 Xác nhận trước khi thay đổi (Approval Required)
- **KHÔNG** tự ý chỉnh sửa code, file cấu hình hoặc thực hiện bất kỳ thay đổi lớn nào trên hệ thống nếu chưa nhận được sự đồng ý/xác nhận từ người dùng.
- Luôn trình bày kế hoạch (`implementation_plan.md`) hoặc nội dung thay đổi dự kiến và chờ người dùng duyệt trước khi thực thi.

### 2. ⚡ Deterministic Routing & Build Verification
- **Routing**: Phân loại yêu cầu qua bảng **[MASTER-ROUTING.md](./MASTER-ROUTING.md)** (R0–R8) trước khi thao tác.
- **Build Verification**: Mọi thay đổi mã nguồn phải được kiểm tra biên dịch (`dotnet build`, `npm run build`...) đảm bảo `0 Error(s)`.

### 3. ☁️ Quy trình Git Realtime & Cloud Safety (Commit & Push Realtime)
- Mỗi khi có thay đổi được chấp thuận và hoàn thành:
  1. **Commit**: Gom nhóm thay đổi và tạo commit với thông điệp rõ ràng theo chuẩn Conventional Commits.
  2. **Push**: Push commit trực tiếp lên remote repository (GitHub).
  3. **Không để mất source**: Đảm bảo toàn bộ mã nguồn được lưu trữ an toàn trên GitHub, tránh mất mát khi reset máy.

### 4. 🌐 Xử lý Trạng thái & Chuỗi Đa ngôn ngữ (Status & Multilingual Matching)
- Khi so sánh, lọc, hoặc đếm các giá trị trạng thái (Status, Role, Type, Category, Leader/Player Name):
  - **KHÔNG** bao giờ so sánh khớp cứng duy nhất chuỗi tiếng Anh (như `status == 'Active'`).
  - **LUÔN** kiểm tra và hỗ trợ đa ngôn ngữ (Tiếng Việt & Tiếng Anh, case-insensitive, `.Trim()`), sử dụng so sánh từ khóa linh hoạt.

### 5. 🎯 Tính Ngắn Gọn & Không Lặp Câu Trả Lời Rập Khuôn (Strict No-Boilerplate)
- **TRỰC TIẾP VÀO TRỌNG TÂM**: TUYỆT ĐỐI KHÔNG lặp lại các câu trả lời rập khuôn mẫu. Trả lời trực tiếp vào nội dung người dùng hỏi.
- **XỬ LÝ DỮ LIỆU ĐA TRƯỜNG**: Tra cứu case-insensitive đa trường (`PlayerName`, `RenderName`, `Metadata`, `Path`).

### 6. 🛡️ Quy tắc Log Chuẩn mực & Không Nuốt Lỗi (No Silent Exception)
- **KHÔNG NUỐT NGOẠI LỆ**: Tuyệt đối không bắt catch mà nuốt lỗi khiến trả về kết quả rỗng không rõ nguyên nhân.
- **MÃ LỖI MINH BẠCH**: Gắn Error Code và context chi tiết (`execution_time_ms`, `retry_count`, `target_entity_id`) khi xảy ra lỗi.

### 7. 🧠 Self-Evolving Knowledge Base
- Ghi lại nguyên nhân gốc rễ và giải pháp vào **[knowledge-base/FIELD_JOURNAL.md](./knowledge-base/FIELD_JOURNAL.md)** và cập nhật các `SKILL.md` tương ứng sau mỗi ca fix lỗi thành công.

---

## 🧭 Master Routing Overview

| Route | Domain / Task Category | Skill Reference |
|---|---|---|
| **R0** | Scope Check & Task Classification | `rules/01-routing-contract.md` |
| **R1** | C# Build & Compilation Diagnostics | `skills/csharp-build-diagnostics/SKILL.md` |
| **R2** | Game Memory Offsets & Reversing | `skills/poe-memory-offset-reversing/SKILL.md` |
| **R3** | Bot Navigation & Stuck Recovery | `skills/bot-navigation-stuck-fixer/SKILL.md` |
| **R4** | Boss Encounter Logic & Timing | `skills/boss-encounter-tuning/SKILL.md` |
| **R5** | Single-File Executable Packaging | `skills/single-file-packager-deployment/SKILL.md` |
| **R6** | Trade Buyer & Stash Automation | `skills/trade-buyer-diagnostics/SKILL.md` |
| **R7** | Self-Evolving Knowledge Logging | `skills/self-evolving-knowledge-base/SKILL.md` |
| **R8** | Git Realtime Sync & Source Safety | `skills/git-realtime-sync/SKILL.md` |

---

## 📂 System Directory Structure

```
.agents/
├── AGENTS.md                  # Main entrypoint & unified rules
├── RULES.md                   # Global execution rules & safety constraints
├── MASTER-ROUTING.md          # Deterministic decision ladder (R0-R8)
├── scripts/
│   ├── refresh-tool-index.ps1 # Toolchain validation script
│   ├── verify-build-health.ps1# Build verification script
│   └── sync-github.ps1        # Realtime GitHub synchronization script
├── rules/
│   ├── 01-routing-contract.md
│   ├── 02-memory-safety-rules.md
│   ├── 03-ui-and-threading-rules.md
│   ├── 04-packaging-rules.md
│   └── 05-git-realtime-sync.md
├── skills/
│   ├── poe-memory-offset-reversing/SKILL.md
│   ├── csharp-build-diagnostics/SKILL.md
│   ├── bot-navigation-stuck-fixer/SKILL.md
│   ├── boss-encounter-tuning/SKILL.md
│   ├── single-file-packager-deployment/SKILL.md
│   ├── trade-buyer-diagnostics/SKILL.md
│   ├── self-evolving-knowledge-base/SKILL.md
│   └── git-realtime-sync/SKILL.md
└── knowledge-base/
    ├── FIELD_JOURNAL.md
    └── COMMON_PATTERNS.md
```
