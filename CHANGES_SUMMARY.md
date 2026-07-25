# Tóm tắt thay đổi (phiên làm việc gần nhất)

Lưu ý: bảng này dựng từ lịch sử thao tác trong phiên chat (sandbox chạy `git status`/`git diff --stat` hiện không dùng được do hết dung lượng đĩa) — nên chạy `git status --porcelain` / `git diff --stat` để đối chiếu lại cho chắc trước khi commit/review.

## File mới / đã sửa (code)

| File | Trạng thái | Ai tạo/sửa | Mô tả |
|---|---|---|---|
| `gen_user_data/schemas_v2.py` | Mới | Claude | Đề xuất schema v2 cho `UserProfile` (tách `explicit_preferences` vs `inferred_attributes`) và `RecommendationEvent`/`Interaction` (tách retrieval+generation log khỏi hành động user). Không đè `schemas.py` gốc. Đã sửa: `has_children`(bool) → `children`(int 0-10); `preferred_districts`/`property_type` đổi nguồn validate từ `config/distribution_config.py` (mô phỏng) sang dữ liệu thật (`vocab_real_data.py` + `districts_real.json`). |
| `gen_user_data/config/vocab_real_data.py` | Mới | Claude | Danh sách category đã xác nhận đầy đủ từ `Data/Final_Data.csv` thật: `PROPERTY_TYPES_REAL` (2 giá trị: Căn hộ/Nhà đất), `LEGAL_STATUS_REAL` (4 giá trị, gồm "Không rõ"), `FURNISHING_REAL` (4 giá trị), `DIRECTIONS_REAL` (8 hướng). |
| `gen_user_data/extract_vocab.py` | Mới | Claude | Script dùng `pandas.read_csv` đọc `Data/Final_Data.csv`, xuất value_counts cho các field category + danh sách quận/phường thật. |
| `Data/convert_csv_to_json_xlsx.py` | Mới | Claude | Script sinh lại `Final_Data.json`/`Final_Data.xlsx` từ `Final_Data.csv` (CSV là nguồn chuẩn). |

## File dữ liệu mẫu (gen_user_data/data/)

| File | Trạng thái | Ai tạo/sửa | Mô tả |
|---|---|---|---|
| `users_v2_sample.json` | Mới | Claude | 2 bản ghi `UserProfile` mẫu theo schema v2, dùng tên phường thật sau sáp nhập (`Phường An Khánh`, `Phường Long Bình`). |
| `recommendation_events_v2_sample.json` | Mới | Claude | 1 bản ghi `RecommendationEvent` mẫu — top-10 `recommended_items`, nhưng chỉ top-3 có `llm_output` (khớp hành vi hệ thống thật: backend chỉ gửi top-3 cho Gemini). |
| `interactions_v2_sample.json` | Mới → bị xoá → khôi phục | Claude (khôi phục), Bạn (đã xoá trước đó) | Bạn từng xoá file này vì nghĩ không cần cho evaluation; đã khôi phục vì các metric ranking truyền thống (NDCG/Precision/Recall/MRR/MAP/HitRate) cần ground-truth từ hành vi user thật (view/save/contact), không thể lấy từ `RecommendationEvent` một mình. |

## File sinh ra bằng cách chạy script (trên máy bạn)

| File | Trạng thái | Ai tạo/sửa | Mô tả |
|---|---|---|---|
| `gen_user_data/config/districts_real.json` | Mới | Bạn (chạy `extract_vocab.py`) | 112 phường/xã thật kèm tần suất, rút từ `Final_Data.csv`. |
| `gen_user_data/config/vocab_report.json` | Mới | Bạn (chạy `extract_vocab.py`) | value_counts đầy đủ cho `property_type`, `legal_status`, `furnishing`, `house_direction`, `balcony_direction`, `listing_type`. |
| `Data/Final_Data.json` | Ghi đè | Bạn (chạy `convert_csv_to_json_xlsx.py`) | Sinh lại từ CSV — đã verify khớp 3037/3037 bản ghi, không còn field tiếng Việt cũ. |
| `Data/Final_Data.xlsx` | Ghi đè | Bạn (chạy `convert_csv_to_json_xlsx.py`) | Sinh lại từ CSV — Claude chưa verify được nội dung (file binary, sandbox không đọc được). |
| `Data/Cũ.json` | Mới | Bạn | Bản backup thủ công của `Final_Data.json` gốc (crawl thô) trước khi bị ghi đè — không phải do Claude tạo. |

## Không đổi (để tham chiếu)

`Data/Final_Data.csv` — giữ nguyên toàn bộ, là nguồn chuẩn duy nhất cho cả 2 file trên.

`gen_user_data/schemas.py`, `recommender.py`, `run_eval.py` và toàn bộ pipeline backend — **không đụng tới**, `schemas_v2.py` chỉ là bản đề xuất song song để review/migrate dần.
