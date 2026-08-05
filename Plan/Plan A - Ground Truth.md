# Plan A — Ground truth 2 tầng theo Phường/Xã (`gen_user_data/`)

## Context

Eval cho thấy precision/recall/NDCG thấp bất thường (đã điều tra chi tiết
trong `Evaluation/EVAL_PLAN.md` và `Evaluation/README.md`). Nguyên nhân gốc:
`relevance_v2()` (`gen_user_data/generation/gen_v2.py:171-198`) chỉ cho
trường `district` (giá trị thật là **Phường/Xã** sau sáp nhập, vd
`"Phường Thới Hòa"` — KHÔNG phải "Quận" cũ) 20% trọng số (2.0/10) trong tổng
điểm, và mỗi event chỉ xếp hạng trên 500/3030 listing lấy ngẫu nhiên — nên
top-10 "ground truth" thường trải trên 6-7 phường/xã khác nhau, trong khi hệ
thống search thật lọc theo `district` kiểu **cứng** (SQL `AND`, loại thẳng
nếu sai phường/xã — `backend/src/search/repository.py::_where()`). Kết quả:
hệ thống bị đánh giá thấp vì lý do không liên quan tới chất lượng ranking
thật.

Quyết định: nâng trọng số `district` lên mức gần như quyết định tuyệt đối,
cụ thể qua thiết kế 2 tầng — đúng phường/xã luôn đứng trước, phường/xã khác
chỉ bù khi thiếu — làm ground truth nội tại nhất quán.

(Xem thêm [`Plan B - Backend.md`](Plan%20B%20-%20Backend.md) — tính năng
fallback khu vực tương ứng trên hệ thống thật, độc lập với plan này, có thể
làm trước.)

---

## 1. `gen_user_data/catalog.py`
Thêm 1 hàm mới, đặt cạnh `derive_pools()`:
```python
def build_district_index(listings: List[Listing]) -> Dict[str, List[int]]:
    """district (Phường/Xã) -> danh sách index trong `listings`. Build 1 lần,
    dùng lại xuyên suốt generate_events_interactions_v2 để không phải quét
    lại catalog mỗi event."""
    idx: Dict[str, List[int]] = {}
    for i, l in enumerate(listings):
        idx.setdefault(l.district, []).append(i)
    return idx
```

## 2. `gen_user_data/generation/gen_v2.py` — nâng trọng số `district` lên quyết định

Nói đơn giản: thay vì `district` chỉ chiếm 20% điểm như hiện tại
(`relevance_v2()`, dòng 171-198), biến nó thành **tiêu chí quyết định trước
tiên** — đúng phường/xã user thích thì luôn được xếp lên đầu, các tiêu chí
còn lại (giá/loại nhà/phòng ngủ/tiện ích) chỉ dùng để xếp thứ tự *trong*
nhóm đó. Cụ thể:

1. Viết hàm điểm phụ mới `secondary_relevance(user, listing)` — **giống hệt
   công thức `relevance_v2` hiện tại nhưng bỏ hẳn phần cộng điểm `district`**
   (chỉ còn giá + loại nhà + phòng ngủ + tiện ích, tổng trọng số 8.0 thay vì
   10.0). `relevance_v2()` cũ giữ nguyên, không xoá, không dùng nữa trong
   luồng sinh event.
2. Thêm `select_tier_candidates(user, catalog, district_index, target_district, top_k=TOP_K)`:
   - **Tầng 1**: toàn bộ listing có `district == target_district`, xếp theo
     `secondary_relevance` giảm dần (dùng `argsort(..., kind="stable")` để
     kết quả tất định khi trùng điểm — phường/xã nhỏ dễ trùng).
   - **Tầng 2**: chỉ khi tầng 1 chưa đủ `top_k`, bù thêm listing tốt nhất
     (cùng `secondary_relevance`) từ **các phường/xã khác**, đủ tới `top_k`.
   - Nối tầng 1 trước + tầng 2 sau, **luôn** giữ đúng thứ tự này (tầng 1 luôn
     đứng trên tầng 2 bất kể điểm số — đây chính là "trọng số district gần
     như tuyệt đối", thể hiện bằng thứ tự tầng thay vì 1 con số trọng số).
3. Trong `generate_events_interactions_v2()` (dòng 230-334):
   - Bỏ dòng lấy mẫu ngẫu nhiên `pool_idx = rng.choice(..., size=min(500, ...))`
     — **quét toàn bộ ~3030 listing** thay vì 500 ngẫu nhiên (rẻ, chạy 1 lần
     lúc sinh dữ liệu offline, không phải lúc user query thật).
   - `district_index = build_district_index(catalog)` — build 1 lần, đặt gần
     `amen_sim = _load_amenity_sim()`.
   - Thay khối chọn ứng viên cũ bằng:
     ```python
     target_district = str(rng.choice([x.value for x in user.explicit_preferences.preferred_districts]))
     top = select_tier_candidates(user, catalog, district_index, target_district, top_k=TOP_K)
     lead = top[0][0]
     ... (raw_query giữ nguyên logic cũ, tự nhiên sẽ nhắc đúng phường/xã vì lead luôn ở target_district khi tầng 1 không rỗng) ...
     filters = {"district": target_district}   # suy ra trực tiếp, không random 1 lần nữa
     ```
   - Phần còn lại (`rec_items`, `_rerank_and_explain`, sinh interactions)
     không cần sửa — đã xác nhận qua đọc toàn bộ hàm, chỉ đọc `top` như
     `List[(Listing, float)]` chung chung.

## 3. Giảm tổng số event từ ~1055 xuống ~500

Số event hiện tại = tổng qua 200 user của `ceil(T / 3)` với
`T ~ clip(Poisson(15), 10, 20)` (config hiện tại,
`gen_user_data/config/distribution_config.py:16-20`) → trung bình ~5
event/user × 200 user ≈ 1000-1055, khớp con số thực tế đã quan sát.

Để còn **~500 event** (500 query, mỗi query top-10), sửa
`gen_user_data/config/distribution_config.py`:
```python
INTERACTIONS_PER_USER_LAMBDA = 7   # từ 15
MIN_INTERACTIONS_PER_USER = 5      # từ 10
MAX_INTERACTIONS_PER_USER = 10     # từ 20
```
Trung bình T≈7 → `ceil(T/3)`≈2.5-3 event/user × 200 user ≈ 500-540 event.
Đây là số **xấp xỉ** (do lấy mẫu Poisson ngẫu nhiên), không chốt đúng 500
tuyệt đối — chạy thử 1 lần rồi xem con số in ra (`generate_all_v2.py` in
tổng số event) để tinh chỉnh lại `INTERACTIONS_PER_USER_LAMBDA` nếu cần sát
hơn.

## 4. `Evaluation/adapters.py` — sửa kèm theo (bắt buộc, không tuỳ chọn)
`translate_filters_for_live()` (dòng 161-187) hiện gửi **toàn bộ**
`preferred_districts` của user lên hệ thống thật — đây là bản vá cho ground
truth CŨ (district chỉ 20% trọng số nên trải nhiều phường/xã). Sau khi sửa
xong, ground truth tầng 1 đã gắn với đúng 1 phường/xã xác định
(`filters["district"]` mới) — tiếp tục gửi cả danh sách sẽ:
- Làm filter gửi lên **rộng hơn** thực tế ground truth được xây (lệch theo
  chiều ngược lại).
- Khiến tính năng fallback khu vực (xem Plan B) gần như không bao giờ được
  kích hoạt khi chạy eval (filter đa-khu-vực hiếm khi trả về rỗng).

**Sửa**: bỏ hẳn khối override, để `filters["district"]` đi thẳng từ
`event["context"]["filters_applied"]["district"]` (giờ đã là 1 chuỗi đúng).
Cập nhật lại docstring hàm này + đoạn liên quan trong `Evaluation/README.md`
(mục "Lưu ý khi đọc kết quả") cho khớp lý do mới.

## 5. Không cần sửa (đã xác nhận)
- `prep_rerank.py`, `apply_rerank.py` — xử lý `recommended_items`/`llm_output`
  chung chung, không phụ thuộc nội bộ phường/xã/`relevance_v2`.
- `Evaluation/adapters.py::ground_truth_k()` — đã đọc `len(recommended_items)`
  động, luôn = 10 vì tầng 1+2 luôn đủ (catalog ~3030 listing, phường/xã nhỏ
  nhất có 1 listing, các phường/xã khác luôn đủ bù tầng 2).
- Pipeline v1 (`run_eval.py`, `load_all.py`, `precompute.py`, `similarity_kg.py`,
  `kg/build_kg.py`) — không đọc file v2, không gọi `relevance_v2`.

---

## Thứ tự triển khai

1. **Sửa code** — `catalog.py` (mục 1), `gen_v2.py` (mục 2), giảm số event
   trong `distribution_config.py` (mục 3).
2. **Chạy thử nhỏ** — script adhoc build 1 catalog giả nhỏ (vài listing
   phường A, vài phường B), gọi `select_tier_candidates` — xác nhận: đủ
   phường A thì chỉ trả phường A xếp đúng thứ tự điểm; thiếu thì bù phường B
   nối sau, tổng đúng `top_k`. `secondary_relevance` không đổi theo phường
   (sanity check không rò rỉ điểm district vào).
3. **Chạy full pipeline sinh dữ liệu**:
   ```bash
   cd gen_user_data
   python generate_all_v2.py     # -> recommendation_events_v2.json (bản mới, ~500 event)
   python prep_rerank.py         # -> scratchpad/rerank/batch_*.json
   # --- chạy workflow Claude-agent rerank bên ngoài (thủ công/agentic) ---
   python apply_rerank.py        # -> recommendation_events_v2_claude.json (bản cuối)
   ```
   Bước rerank-workflow là thủ công/ngoài script, mất thời gian — nên bắt
   đầu sớm, đừng để thành điểm nghẽn cuối cùng.
4. In thống kê sau khi có `recommendation_events_v2.json` mới: tổng số event
   sinh ra (kỳ vọng ~500), và trong 10 `recommended_items` mỗi event có bao
   nhiêu item cùng `filters_applied["district"]` (kỳ vọng tăng mạnh so với
   baseline ~1/10 trước đây).
5. **Sửa `Evaluation/adapters.py`** (mục 4) ngay sau khi có
   `recommendation_events_v2_claude.json` mới.
6. **Chạy lại `Evaluation/run_eval.py`** để xác nhận cải thiện:
   ```bash
   cd Evaluation && python run_eval.py --limit 100
   ```
   So precision/recall/NDCG với baseline đã ghi
   (`Evaluation/results/20260805T142916_n97/summary.json`) — kỳ vọng tăng rõ
   rệt, đến từ ground truth nhất quán hơn chứ không phải ranking thay đổi.
   Đồng thời xác nhận tính năng fallback khu vực ở Plan B thực sự được kích
   hoạt qua đường eval (một số query sẽ rơi vào trường hợp 0 kết quả đúng
   phường/xã → kích hoạt fallback).
