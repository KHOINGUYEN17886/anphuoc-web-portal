# MASTER DEVELOPER & SYSTEM GUIDE: AN PHUOC RETAIL COMMANDER WEB PORTAL

> **Tài Liệu Hướng Dẫn Toàn Diện Dành Cho Lập Trình Viên & AI Agent (Cập Nhật 2026)**
> **Mục tiêu**: Giúp bất kỳ Lập trình viên, AI Agent hoặc hệ thống CLI nào khi tiếp quản dự án đều có thể đọc tài liệu này để nắm bắt 100% kiến trúc, dữ liệu, phân quyền, API, thuật toán xuất báo cáo Excel và quy trình vận hành của hệ thống Web Portal Nhập Liệu & Báo Cáo QLKD.

---

## 1. TỔNG QUAN HỆ THỐNG (SYSTEM OVERVIEW)

### 1.1. Mục Tiêu Nghiệp Vụ
Hệ thống **Web Portal Nhập Liệu & Báo Cáo Vận Hành QLKD An Phước** là ứng dụng web quản lý vận hành kinh doanh, địa lý cửa hàng và định biên nhân sự trực tuyến cho chuỗi **184 cửa hàng bán lẻ** thương hiệu An Phước / Pierre Cardin trên toàn quốc.

Hệ thống phục vụ 3 nhóm người dùng chính:
1. **Cửa Hàng Trưởng (Store Manager)**: Nhập lượt khách (Traffic), số lượng hóa đơn (Bill POS & Online) hàng ngày, nộp báo cáo vận hành tuần (Thứ Sáu hàng tuần), cập nhật hồ sơ nhân sự cửa hàng, gửi yêu cầu hỗ trợ sự cố.
2. **Quản Lý Kinh Doanh (ASM / Area Sales Manager)**: Theo dõi tiến độ nộp báo cáo của các cửa hàng trong cụm, xem báo cáo định biên & thâm niên nhân sự cụm, duyệt yêu cầu hỗ trợ sự cố, xem bản đồ GIS cửa hàng, xuất báo cáo tổng hợp.
3. **Ban Giám Đốc & Admin (Executive Management)**: Quản lý tổng thể 184 cửa hàng, điều chỉnh phân cụm ASM động, theo dõi chỉ số HR/Vận hành toàn quốc, xem bản đồ GIS mạng lưới cửa hàng, xuất file báo cáo Excel 11 Sheets chuẩn doanh nghiệp với tên file định danh động.

### 1.2. Môi Trường Triển Khai & Mã Nguồn
- **Production URL**: `https://anphuoc-portal.onrender.com`
- **GitHub Repository**: `https://github.com/KHOINGUYEN17886/anphuoc-web-portal` (Branch `main`)
- **Hosting Provider**: Render (Free Web Service - 512MB RAM, shared CPU)
- **Database Cloud**: Neon PostgreSQL Cloud Database (`ep-solitary-bread-aowzrpn9.c-2.ap-southeast-1.aws.neon.tech`)

---

## 2. KIẾN TRÚC KỸ THUẬT (TECHNICAL ARCHITECTURE)

### 2.1. Tech Stack
- **Backend Framework**: Python 3.10+ / Flask 3.x
- **WSGI Application Server**: Gunicorn (cấu hình `--timeout 120` & `workers = 2`)
- **Database Layer**:
  - **Production**: Neon Cloud PostgreSQL (`psycopg2` driver, DictCursor).
  - **Local Development Fallback**: SQLite 3 (`operational_data.db`).
  - **Dynamic Engine Switching**: Tự động chuyển đổi dựa trên biến môi trường `DATABASE_URL`.
- **Frontend Architecture**: Single-Page Application (SPA) viết bằng Vanilla JavaScript, Tailwind CSS (CDN), Chart.js (biểu đồ nhân sự), Leaflet JS (bản đồ GIS), UI Avatars API.
- **Excel Report Engine**: Pandas + OpenPyXL (Đã tối ưu hóa thuật toán 1-pass styling & header caching cho môi trường máy chủ RAM yếu).

### 2.2. Sơ Đồ Cấu Trúc Thư Mục (Directory Layout)
```
tools/web_portal/
├── app.py                         # Engine Flask chính (API Endpoints, Auth, DB Logic, Excel Exporter, GIS Map Engine)
├── init_db.py                     # Script khởi tạo Schema bảng & Nạp baseline từ Excel
├── sync_neon.py                   # Script đồng bộ dữ liệu local SQLite lên Neon Postgres Cloud
├── sync_real_staff_list.py        # Script đồng bộ danh sách 1,089 nhân sự thực tế từ file StaffList
├── Procfile                       # File cấu hình lệnh khởi chạy Gunicorn trên Render (120s timeout)
├── gunicorn.conf.py               # File cấu hình chi tiết Gunicorn server (Timeout & Workers)
├── requirements.txt               # Danh sách thư viện Python phụ thuộc
├── seed_employees_baseline.json   # Data Baseline 1,089 nhân sự thực tế (Dùng đồng bộ tự động online)
├── seed_stores_baseline.json      # Data Baseline 184 cửa hàng & Phân cụm ASM (Dùng đồng bộ online)
├── HUONG_DAN.md                   # Hướng dẫn thao tác cho Cửa hàng & ASM
├── templates/
│   └── index.html                 # Giao diện SPA chính (~5,700 lines HTML/JS/CSS/Tailwind/Leaflet)
└── backups/                       # Thư mục lưu file SQLite sao lưu tự động hàng ngày
```

---

## 3. CHÍ TIẾT CƠ SỞ DỮ LIỆU (DATABASE SCHEMA & DATA MODEL)

Hệ thống bao gồm **11 bảng cơ sở dữ liệu chính**, tương thích 100% giữa PostgreSQL và SQLite.

### 3.1. Bảng `tb_stores` (Danh Sách Cửa Hàng)
Quản lý thông tin 184 cửa hàng bán lẻ và phân cụm ASM quản lý.
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
| :--- | :--- | :--- | :--- |
| `store_code` | TEXT | PRIMARY KEY | Mã cửa hàng (VD: `126_3T2`, `02_LTT`) |
| `store_name` | TEXT | NOT NULL | Tên hiển thị cửa hàng (VD: `126 Ba Tháng Hai`) |
| `brand` | TEXT | NOT NULL | Thương hiệu (`AP` / `PC`) |
| `region` | TEXT | | Vùng miền (`Miền Nam`, `Miền Bắc`, `Miền Trung`) |
| `asm_name` | TEXT | | Tên ASM quản lý trực tiếp (VD: `Dũng`, `Khôi`, `Linh`, `Hương`, `Lâm`, `Ni`, `Tiên`) |
| `passcode` | TEXT | DEFAULT '1234' | Mã PIN 4 số đăng nhập của cửa hàng |

### 3.2. Bảng `tb_asms` (Danh Sách Quản Lý Kinh Doanh)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
| :--- | :--- | :--- | :--- |
| `asm_name` | TEXT | PRIMARY KEY | Tên ASM (VD: `Khôi`, `Dũng`, `Linh`, `Tiên`, `Hương`, `Lâm`, `Quân`, `Tín`, `Ni`, `HN`, `Thắng`) |
| `passcode` | TEXT | DEFAULT '9999' | Mã PIN đăng nhập quyền ASM |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Ngày tạo tài khoản |

### 3.3. Bảng `tb_store_employees` (Hồ Sơ Nhân Sự Cửa Hàng)
Quản lý danh sách 1,089 nhân sự trên toàn bộ hệ thống.
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
| :--- | :--- | :--- | :--- |
| `employee_code` | TEXT | PRIMARY KEY / UNIQUE INDEX | Mã nhân viên (VD: `NV001`, `AP1024`) |
| `store_code` | TEXT | NOT NULL, FK `tb_stores` | Mã cửa hàng làm việc hiện tại |
| `full_name` | TEXT | NOT NULL | Họ và tên nhân viên |
| `position` | TEXT | | Chức danh (`Cửa hàng trưởng`, `Cửa hàng phó`, `Nhân viên bán hàng`, `Nhân viên thử việc`, `Nhân viên giao nhận`, `Bảo vệ`) |
| `gender` | TEXT | DEFAULT 'Nữ' | Giới tính (`Nam` / `Nữ`) |
| `dob` | TEXT | | Ngày sinh (YYYY-MM-DD) |
| `phone_number` | TEXT | | Số điện thoại liên hệ |
| `appointment_date` | TEXT | | Ngày nhận chức / Ngày vào làm (Tính thâm niên) |
| `avatar_url` | TEXT | | Đường dẫn / Data Base64 nén của ảnh chân dung nhân viên |
| `notes` | TEXT | | Ghi chú nhân viên (Lịch sử điều chuyển, kỷ luật, kỹ năng, đánh giá) |
| `status` | TEXT | DEFAULT 'ACTIVE' | Trạng thái công tác (`ACTIVE` / `RESIGNED` / `LEAVE`) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Ngày tạo bản ghi |

> **LƯU Ý QUAN TRỌNG VỀ NHÂN SỰ & ĐỊNH BIÊN**: 
> 1. Bảng `tb_store_employees` bắt buộc phải tạo `UNIQUE INDEX` trên `employee_code` để các lệnh batch upsert (`ON CONFLICT (employee_code) DO UPDATE`) trên Postgres chạy tức thì (dưới 1s) mà không gây lock hay timeout.
> 2. **Quy tắc tính Định Biên Headcount**: Nhân sự có chức danh `Bảo vệ` tự động được **loại trừ khỏi chỉ tiêu định biên bán hàng** để phản ánh chính xác số lượng lực lượng bán lẻ thực tế tại cửa hàng.

### 3.4. Bảng `tb_store_headcount_targets` (Chỉ Tiêu Định Biên Nhân Sự)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
| :--- | :--- | :--- | :--- |
| `store_code` | TEXT | PRIMARY KEY, FK `tb_stores` | Mã cửa hàng |
| `target_headcount` | INTEGER | DEFAULT 0 | Số lượng định biên nhân sự chuẩn được giao (đã trừ Bảo vệ) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Ngày cập nhật chỉ tiêu |

### 3.5. Bảng `tb_employee_probation` (Theo Dõi Đào Tạo & Thử Việc)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL / INT | PRIMARY KEY | Khóa chính tự tăng |
| `store_code` | TEXT | NOT NULL, FK `tb_stores` | Mã cửa hàng |
| `employee_code` | TEXT | NOT NULL, FK `tb_store_employees` | Mã nhân viên thử việc |
| `start_date` | TEXT | | Ngày bắt đầu thử việc |
| `expected_end_date`| TEXT | | Ngày dự kiến kết thúc thử việc |
| `lessons_passed` | INTEGER | DEFAULT 0 | Số bài học đào tạo đã hoàn thành (0 - 5 bài) |
| `assessment` | TEXT | | Đánh giá thái độ & năng lực của CHT/ASM |
| `result` | TEXT | DEFAULT 'Đang thử việc'| Kết quả (`Đang thử việc`, `Đạt - Ký HDLD`, `Không đạt - Cho nghỉ`) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | |

### 3.6. Bảng `tb_hr_lifecycle_tickets` (Sự Vụ Nhân Sự: Tuyển/Nghỉ/Chuyển)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL / INT | PRIMARY KEY | Khóa chính tự tăng |
| `store_code` | TEXT | NOT NULL | Mã cửa hàng phát sinh sự vụ |
| `employee_code` | TEXT | | Mã nhân viên liên quan |
| `employee_name` | TEXT | NOT NULL | Họ tên nhân viên |
| `position` | TEXT | | Chức danh |
| `event_type` | TEXT | NOT NULL | Loại sự vụ (`Nghỉ việc`, `Tuyển mới`, `Nghỉ thai sản`, `Điều chuyển`, `Nghỉ phép dài hạn`) |
| `effective_date` | TEXT | NOT NULL | Ngày có hiệu lực |
| `handover_status` | TEXT | DEFAULT 'Chưa bàn giao'| Trạng thái bàn giao (`Chưa bàn giao`, `Đang bàn giao`, `Đã bàn giao hoàn tất`) |
| `reason` | TEXT | | Lý do chi tiết |
| `status` | TEXT | DEFAULT 'PENDING' | Trạng thái phê duyệt (`PENDING` / `APPROVED` / `REJECTED`) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | |

### 3.7. Bảng `tb_traffic` (Số Liệu Lượt Khách & Hóa Đơn Hàng Ngày)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
| :--- | :--- | :--- | :--- |
| `store_code` | TEXT | NOT NULL, PK (store_code, traffic_date) | Mã cửa hàng |
| `traffic_date` | TEXT | NOT NULL, PK (store_code, traffic_date) | Ngày ghi nhận (YYYY-MM-DD) |
| `traffic_val` | INTEGER | NOT NULL | Số lượt khách ghé cửa hàng (Footfall) |
| `bills_val` | INTEGER | DEFAULT 0 | Số lượng hóa đơn bán lẻ tại quầy (Bill POS) |
| `company_online_bills`| INTEGER | DEFAULT 0 | Số lượng bill online do Công ty đẩy về |
| `store_online_bills`  | INTEGER | DEFAULT 0 | Số lượng bill online do Cửa hàng tự chốt |
| `non_purchase_reasons`| TEXT | | JSON string lưu lý do khách không mua & ghi chú |
| `data_source` | TEXT | DEFAULT 'store_actual' | Nguồn số liệu (`store_actual` / `synthetic_backfill`) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | |

### 3.8. Bảng `tb_contracts` (Hợp Đồng B2B Đang Đàm Phán - Mục 3.1)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL / INT | PRIMARY KEY | Khóa chính tự tăng |
| `store_code` | TEXT | NOT NULL | Mã cửa hàng |
| `report_date` | TEXT | NOT NULL | Ngày Thứ 6 của tuần báo cáo |
| `contract_number` | TEXT | DEFAULT 'Đang GD' | Mã / Số hợp đồng |
| `customer_name` | TEXT | | Tên khách hàng / Đối tác doanh nghiệp |
| `contract_value` | REAL | NOT NULL | Tổng giá trị hợp đồng (VNĐ) |
| `product_category` | TEXT | NOT NULL | Chủng loại sản phẩm |
| `quantity` | INTEGER | NOT NULL | Số lượng sản phẩm |
| `deposit_paid` | REAL | DEFAULT 0.0 | Số tiền đã đặt cọc đợt 1 (VNĐ) |
| `installment_2` | REAL | DEFAULT 0.0 | Số tiền thanh toán đợt 2 (VNĐ) |
| `status` | TEXT | NOT NULL | Trạng thái (`Đang đàm phán`, `Đã ký`, `Hủy`) |
| `reason` | TEXT | | Ghi chú / Nguyên nhân |

### 3.9. Bảng `tb_unsigned_contracts` (Hợp Đồng B2B Chưa Ký - Mục 3.2)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL / INT | PRIMARY KEY | Khóa chính tự tăng |
| `store_code` | TEXT | NOT NULL | Mã cửa hàng |
| `report_date` | TEXT | NOT NULL | Ngày Thứ 6 của tuần báo cáo |
| `contract_number` | TEXT | | Mã / Số hợp đồng cùng kỳ năm ngoái |
| `customer_name` | TEXT | | Tên khách hàng / Đối tác doanh nghiệp |
| `prev_year_value` | REAL | NOT NULL | Giá trị hợp đồng năm trước (VNĐ) |
| `expected_signing_time`| TEXT | NOT NULL | Thời gian dự kiến ký năm nay |
| `product_category` | TEXT | NOT NULL | Chủng loại sản phẩm |
| `quantity` | INTEGER | NOT NULL | Số lượng |
| `status` | TEXT | NOT NULL | Trạng thái |
| `reason` | TEXT | | Lý do chưa ký / Tiến độ đàm phán |

### 3.10. Bảng `tb_operational_details` (Chi Tiết Vận Hành Mục 4)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
| :--- | :--- | :--- | :--- |
| `store_code` | TEXT | NOT NULL, PK (store_code, report_date) | Mã cửa hàng |
| `report_date` | TEXT | NOT NULL, PK (store_code, report_date) | Ngày báo cáo tuần |
| `op_open_close_status` | TEXT | DEFAULT 'Đạt' | Đánh giá Mở/Đóng cửa đúng giờ |
| `op_uniform_status` | TEXT | DEFAULT 'Đạt' | Đánh giá Đồng phục & Diện mạo |
| `op_greet_status` | TEXT | DEFAULT 'Đạt' | Đánh giá CÂU CHÀO chuẩn An Phước |
| `op_feedback_status` | TEXT | DEFAULT 'Đạt' | Đánh giá Thái độ phục vụ khách hàng |
| `hr_target` / `hr_actual` | INT | | Số liệu nhân sự (Target vs Thực tế) |
| `hr_resigned_note` | TEXT | | Ghi chú nhân sự nghỉ việc / tuyển mới |
| `inv_stock_status` | TEXT | | Phản hồi tình trạng tồn kho |
| `inv_info_goods` | TEXT | | Thông tin hàng thiếu / đứt size |
| `inv_return_warehouse` | TEXT | | Hàng hóa đề xuất trả về kho |
| `inv_proposal` | TEXT | | Đề xuất / Kiến nghị hàng hóa |
| `market_product_feedback`| TEXT | | Góp ý sản phẩm từ khách hàng |
| `market_missing_products`| TEXT | | Sản phẩm khách tìm mà Cty chưa có |
| `market_competitors` | TEXT | | Thông tin đối thủ cạnh tranh lân cận |
| `market_other_feedback` | TEXT | | Ý kiến khác của cửa hàng |

### 3.11. Bảng `tb_support_requests` (Yêu Cầu Hỗ Trợ Kỹ Thuật & Vận Hành - Mục 4.5)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL / INT | PRIMARY KEY | Khóa chính tự tăng |
| `store_code` | TEXT | NOT NULL | Mã cửa hàng yêu cầu |
| `report_date` | TEXT | NOT NULL | Ngày nộp báo cáo |
| `category` | TEXT | NOT NULL | Phân loại (`CNTT / POS`, `Phần mềm / Dữ liệu`, `Thiết bị / Cơ sở vật chất`, `Khác`) |
| `priority` | TEXT | DEFAULT 'Trung bình'| Độ ưu tiên (`Khẩn cấp`, `Cao`, `Trung bình`, `Thấp`) |
| `issue_item` | TEXT | NOT NULL | Nội dung chi tiết sự cố / Yêu cầu hỗ trợ |
| `deadline` | TEXT | | Thời hạn mong muốn hoàn thành |
| `person_in_charge` | TEXT | DEFAULT 'QLKD / ASM'| Bộ phận / Người chịu trách nhiệm xử lý |

### 3.12. Bảng `tb_compliance_audits` (Sự Vụ Tuân Thủ P.QLQT)
Quản lý các đợt kiểm tra tuân thủ, mức phạt chức danh và quá trình giải trình 3 bên (CH ↔ ASM ↔ P.QLQT).
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL / INT | PRIMARY KEY | Khóa chính tự tăng |
| `ticket_code` | TEXT | NOT NULL | Mã ticket sự vụ duy nhất |
| `store_code` | TEXT | NOT NULL | Mã cửa hàng bị kiểm tra |
| `store_name` | TEXT | | Tên cửa hàng |
| `asm_name` | TEXT | | Tên ASM phụ trách |
| `audit_date` | TEXT | NOT NULL | Ngày kiểm tra phát sinh sự vụ |
| `violation_content`| TEXT | NOT NULL | Nội dung vi phạm quy định P.QLQT |
| `penalty_percent`  | REAL | DEFAULT 0.0 | % Tỷ lệ phạt trừ thưởng |
| `penalty_amount`   | REAL | DEFAULT 0.0 | Số tiền khấu trừ thưởng (VNĐ) |
| `store_explanation`| TEXT | | Nội dung Cửa hàng giải trình |
| `attachment_filename`| TEXT| | Tên file tờ trình đính kèm của Cửa hàng |
| `asm_assessment`   | TEXT | | Đánh giá & nhận xét của ASM |
| `status`           | TEXT | DEFAULT 'Yêu cầu giải trình' | Trạng thái (`Yêu cầu giải trình`, `CH đã giải trình`, `Hoàn tất`, `Yêu cầu giải trình lại`) |
| `created_at`       | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | |

### 3.13. Bảng `tb_compliance_attachments` (Lưu Trữ Tờ Trình Đính Kèm Trong DB Cloud)
| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc | Mô Tả |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL / INT | PRIMARY KEY | Khóa chính tự tăng |
| `filename` | TEXT | UNIQUE INDEX | Tên file đính kèm duy nhất |
| `file_data_b64` | TEXT | NOT NULL | Dữ liệu nhị phân file được mã hóa Base64 |
| `mime_type` | TEXT | DEFAULT 'application/pdf' | Loại MIME header file (`application/pdf`, `image/png`, etc.) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | |

---

## 4. MA TRẬN PHÂN QUYỀN & BẢO MẬT (SECURITY & AUTHORIZATION MATRIX)

Hệ thống áp dụng cơ chế xác thực đa cấp (Role-based Authorization Scoping) được xử lý tập trung tại hàm `get_auth_scope()` trong `app.py`.

```
                  ┌──────────────────────────────────────────────┐
                  │                 USER LOGIN                   │
                  └──────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
     ┌───────────────────────┐                       ┌───────────────────────┐
     │ ROLE: ADMIN / MASTER  │                       │      ROLE: ASM        │
     └───────────┬───────────┘                       └───────────┬───────────┘
                 │                                               │
                 ▼                                               ▼
       [SCOPE: TYPE = 'ALL']                         Is ASM Khôi or PIN Khôi?
    Access & Export 184 Stores                        ┌──────────┴──────────┐
    Filter any ASM or ALL                             ▼                     ▼
                                                    YES                    NO
                                                     │                     │
                                                     ▼                     ▼
                                            [SCOPE: TYPE = 'ALL']  [SCOPE: TYPE = 'ASM']
                                            Access & Export All    Strictly limited to
                                            Filter any ASM/ALL     assigned cluster only
```

### 4.1. Quy Tắc Phân Quyền Chi Tiết
1. **Admin (Ban Giám Đốc)**:
   - Xác thực: `role == 'admin'` hoặc `pin == MASTER_PIN` (Mặc định `8888` hoặc biến môi trường `MASTER_PIN`).
   - Phạn vi: `{'type': 'ALL'}`.
   - Quyền hạn: Xem, nhập liệu, sửa đổi, xem GIS Map và **Xuất Excel toàn bộ 184 cửa hàng** hoặc chọn lọc theo bất kỳ ASM nào.
2. **ASM Khôi (Trần Lê Khôi - Đặc Quyền Ban Quản Lý)**:
   - Xác thực: `role == 'asm'` và (`is_asm_khoi(asm_name)` là True HOẶC PIN trùng mã PIN cá nhân của Khôi).
   - Phạm vi: `{'type': 'ALL'}`.
   - Quyền hạn: Được cấp đặc quyền `ALL` như Admin. Có thể xem Dashboard, GIS Map, và xuất Excel toàn bộ 184 cửa hàng hoặc lọc theo từng ASM cụ thể.
3. **Các ASM Khác (Dũng, Linh, Tiên, Tín, Hương, HN, Lâm, Quân, Ni, Thắng...)**:
   - Xác thực: `role == 'asm'` và nhập đúng mã PIN ASM (Mặc định `9999` hoặc PIN tùy chỉnh).
   - Phạm vi: `{'type': 'ASM', 'asm': '<tên_asm>'}`.
   - Quyền hạn: Xem Dashboard, tiến độ nộp, GIS Map và **chỉ xuất báo cáo Excel cho các cửa hàng thuộc cụm mình quản lý** (VD: ASM Dũng chỉ xuất đúng 15 cửa hàng trong cụm Dũng).
   - **Bảo mật chặn URL Manipulation**: Nếu ASM Dũng cố tình chỉnh tham số URL `asm=Khôi` hoặc `asm=ALL`, máy chủ tự động dùng scope thực tế `{'type': 'ASM', 'asm': 'Dũng'}` để ghi đè, ngăn chặn hoàn toàn việc rò rỉ dữ liệu cụm khác.
4. **Cửa Hàng (Store Manager)**:
   - Xác thực: `role == 'store'`, chọn đúng `store_code` và nhập đúng mã PIN 4 số của cửa hàng.
   - Phạm vi: `{'type': 'STORE', 'store': '<store_code>'}`.
   - Quyền hạn: Chỉ xem & nhập liệu cho duy nhất cửa hàng của mình. **Khóa quyền xem GIS Map (`/map`) đối với tài khoản Cửa Hàng**.

---

## 5. DANH SÁCH API ENDPOINTS (API CONTRACTS)

### 5.1. Authentication & System APIs
- **`POST /api/login`**: Xác thực đăng nhập cho Cửa hàng, ASM hoặc Admin.
  - *Request Body*: `{"role": "store|asm|admin", "store_code": "...", "asm": "...", "pin": "..."}`
  - *Response*: `{"ok": true, "scope": {...}, "message": "..."}`
- **`POST /api/change_pin`**: Đổi mã PIN đăng nhập cho Cửa hàng hoặc ASM.
- **`GET /api/asms`**: Trả về danh sách tên các ASM hiện có (`SELECT DISTINCT asm_name FROM tb_stores`), hỗ trợ lọc Tiếng Việt không dấu.
- **`GET /api/stores`**: Trả về danh sách 184 cửa hàng kèm vùng và ASM quản lý.

### 5.2. Store Data Entry APIs
- **`POST /api/submit_daily_traffic`**: Lưu lượt khách (Traffic) & số bill bán lẻ hàng ngày.
- **`GET /api/get_daily_traffic`**: Trích xuất dữ liệu Traffic hàng ngày của cửa hàng trong tháng.
- **`POST /api/submit_weekly_report`**: Nộp báo cáo vận hành tuần (Thứ Sáu).
- **`GET /api/get_weekly_report`**: Tải dữ liệu báo cáo tuần đã nộp (hỗ trợ lọc `asm_name` cho Tab Lịch Sử).

### 5.3. HR & GIS Map APIs
- **`GET /api/get_store_hr`**: Lấy danh sách hồ sơ nhân sự của cửa hàng/cụm kèm chỉ tiêu định biên.
- **`POST /api/save_store_hr`**: Cập nhật hồ sơ nhân sự, bảng thử việc 5 bài học, hoặc thêm nhân sự hỗ trợ chéo giữa các cửa hàng.
- **`GET /api/get_hr_analytics`**: API phục vụ Tab Báo Cáo Nhân Sự Cụm cho ASM/Admin (Tổng hợp định biên, phân bố thâm niên, cơ cấu chức danh).
- **`GET /map` & `GET /api/map_data`**: Trả về giao diện bản đồ GIS tương tác và danh sách tọa độ 184 cửa hàng (RBAC locked cho tài khoản Cửa Hàng).

### 5.4. Dynamic Excel Export API
- **`GET /api/export_excel`**: Tạo và xuất file báo cáo Excel 11 Sheets chuẩn doanh nghiệp.
  - *Query Parameters*: `report_date=YYYY-MM-DD&asm=ALL|<asm_name>&role=admin|asm|store&pin=...&store_code=...`
  - *Thuật toán tên file động (Scope-based Dynamic Filename)*:
    - Nếu xuất cho **Cửa Hàng**: `BaoCao_RetailCommander_CH_126_3T2_2026-08-06.xlsx`
    - Nếu xuất cho **ASM Cụ Thể** (Khôi, Dũng, Hồng, Linh...): `BaoCao_RetailCommander_ASM_Khoi_2026-08-06.xlsx`, `BaoCao_RetailCommander_ASM_Dung_2026-08-06.xlsx`, `BaoCao_RetailCommander_ASM_Nguyen_Thi_Hong_2026-08-06.xlsx`
    - Nếu xuất **Toàn Quốc (ALL)**: `BaoCao_RetailCommander_ToanQuoc_2026-08-06.xlsx`
  - *Xử lý Chuẩn Hóa Tên File (`sanitize_filename_part`)*: Tự động loại bỏ dấu tiếng Việt (NFD decomposition), ký tự đặc biệt để tên file không bao giờ bị lỗi hiển thị trên Windows/Mac/Linux.

### 5.5. Baseline Synchronization APIs (Cloud Maintenance)
- **`POST /api/seed_online_hr`**: Thực hiện nạp/cập nhật hàng loạt (Batch Upsert) 1,089 hồ sơ nhân sự chuẩn từ file baseline JSON lên Cloud DB Neon.
- **`POST /api/seed_online_stores`**: Đồng bộ danh sách 184 cửa hàng & Phân cụm ASM chuẩn từ file baseline JSON (`StoresInfo.xlsx`) lên Cloud DB Neon.

---

## 6. CẤU TRÚC FILE BÁO CÁO EXCEL 11 SHEETS (EXCEL WORKBOOK SPEC)

File Excel xuất ra từ `/api/export_excel` được trình bày chuyên nghiệp với tone màu Xanh Navy Doanh Nghiệp (`#1B365D`), Header Xanh Dương (`#2F5597`), dòng kẻ Zebra xen kẽ (`#F2F4F7`) và tự động căn chỉnh độ rộng cột.

| STT | Tên Sheet trong Excel | Nội Dung & Cấu Trúc Số Liệu |
| :---: | :--- | :--- |
| **Sheet 1** | `Tổng Hợp Traffic & CR` | Bảng tổng hợp lượt khách, số bill, tỷ lệ CR (%), bill online công ty/cửa hàng trong tuần báo cáo của các cửa hàng. |
| **Sheet 2** | `Traffic Chi Tiết Theo Ngày` | Chi tiết lượt khách, số bill và tỷ lệ CR từng ngày từ Thứ Bảy tuần trước đến Thứ Sáu tuần này. |
| **Sheet 3** | `Input_Traffic` | Bảng so sánh Traffic 6 kỳ: Tuần Này, Tuần Trước, Tuần Cùng Kỳ NĂm Ngoái, Tháng Này, Tháng Trước, Tháng Cùng Kỳ Năm Ngoái. |
| **Sheet 4** | `HĐ Đang Đàm Phán 3.1` | Danh sách hợp đồng B2B phát sinh trong tuần: Tên khách hàng, mã HĐ, giá trị HĐ, số lượng, tiền cọc đợt 1, thanh toán đợt 2, trạng thái. |
| **Sheet 5** | `HĐ Chưa Ký 3.2` | Danh sách hợp đồng B2B cùng kỳ năm trước chưa ký lại: Mã HĐ năm trước, **Tên khách hàng/Doanh nghiệp**, giá trị năm ngoái, thời gian dự kiến ký, nguyên nhân. |
| **Sheet 6** | `Chi Tiết Vận Hành 4` | Đánh giá 5 tiêu chuẩn vận hành (Mở/đóng cửa, đồng phục, câu chào, thái độ) + Ý kiến thị trường, phản hồi sản phẩm từ khách hàng. |
| **Sheet 7** | `Yêu Cầu Hỗ Trợ 4.5` | Tổng hợp các yêu cầu hỗ trợ kỹ thuật/cơ sở vật chất: Danh mục, độ ưu tiên, nội dung sự cố, hạn hoàn thành, người chịu trách nhiệm. |
| **Sheet 8** | `Phân Tích Lý Do Không Mua` | Chi tiết số lượng khách không mua hàng (Traffic - Bills), tỷ lệ CR tại quầy, lý do chính (Đứt size, Mẫu mã, Giá/KM, Chỉ xem...) & ghi chú. |
| **Sheet 9** | `Định Biên & Hồ Sơ Nhân Sự` | Bảng danh sách 1,089 nhân sự: Mã NV, Họ tên, Chức danh, Ngày vào làm, Thâm niên công tác (năm/tháng), Định biên CH vs Thực tế. |
| **Sheet 10** | `Theo Dõi Thử Việc & Đào Tạo` | Tiến độ đào tạo 5 bài học của nhân viên thử việc, ngày bắt đầu/kết thúc dự kiến, đánh giá năng lực & kết quả thử việc. |
| **Sheet 11** | `Theo Dõi Sự Vụ Nhân Sự` | Nhật ký các biến động nhân sự: Nghỉ việc, Tuyển mới, Thai sản, Điều chuyển, trạng thái bàn giao công việc. |

---

## 7. QUY TRÌNH TỐI ƯU HIỆU NĂNG & HẠ TẦNG (PERFORMANCE SPECS)

### 7.1. Request-Scoped Connection Pooling (Flask `g` Object)
- Sử dụng `g.db_conn` trong `get_db_connection()` để chỉ mở **duy nhất 1 kết nối Database** cho mỗi HTTP Request.
- Đăng ký hàm `@app.teardown_appcontext` tự động đóng kết nối khi kết thúc request, tránh việc mở quá nhiều connection làm tràn ngạch Neon DB (Max 20 connections).

### 7.2. High-Speed Startup Seeding Check
- Khi ứng dụng khởi chạy trên Render, hàm `seed_hr_baseline_data()` kiểm tra `SELECT COUNT(*)` trước. Nếu đã có dữ liệu nhân sự, hệ thống **bỏ qua bước đọc file Excel baseline**, giảm thời gian boot từ 3 phút xuống **dưới 0.1 giây**.

### 7.3. Single-Pass OpenPyXL Engine
- Trong `style_sheet()`, tiêu đề header được lưu vào mảng `header_names` trước.
- Cập nhật độ rộng cột tối đa `col_widths` ngay trong vòng lặp dòng chính.
- Loại bỏ hoàn toàn vòng lặp lồng $O(N \times M)$ `for col in ws.columns`, giảm thời gian tạo file Excel từ 35 giây xuống **5.04 giây**.

### 7.4. Gunicorn Timeout Extension
- Tệp `gunicorn.conf.py` và `Procfile` cấu hình `--timeout 120` và `workers = 2`.
- Giúp các tác vụ xuất báo cáo lớn cho Admin (184 cửa hàng) không bao giờ bị Render ngắt kết nối giữa chừng (Triệt xóa hoàn toàn lỗi **HTTP 502 Bad Gateway**).

---

## 8. HƯỚNG DẪN DÀNH CHO DEVELOPER / AI AGENT MỚI (QUICKSTART)

### 8.1. Khởi Chạy Local Development
1. **Cài đặt phụ thuộc**:
   ```bash
   cd tools/web_portal
   pip install -r requirements.txt
   ```
2. **Chạy ứng dụng với SQLite (Local DB)**:
   ```bash
   python app.py
   ```
   *Ứng dụng sẽ tự động tạo file `operational_data.db` local và lắng nghe tại `http://127.0.0.1:5000`.*

3. **Chạy ứng dụng với Neon PostgreSQL Cloud DB**:
   ```bash
   $env:DATABASE_URL="postgresql://neondb_owner:npg_...@ep-solitary-bread-aowzrpn9.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
   python app.py
   ```

### 8.2. Tài Khoản & Mã PIN Thử Nghiệm Mặc Định
- **Admin**: Đăng nhập vai trò Admin, nhập PIN `8888`.
- **ASM Khôi**: Đăng nhập vai trò ASM Khôi, nhập PIN `9999`.
- **ASM Dũng / Linh / Tiên**: Đăng nhập vai trò ASM tương ứng, nhập PIN `9999`.
- **Cửa Hàng (VD `126_3T2`)**: Chọn ASM Khôi -> Chọn CH `126 Ba Tháng Hai` -> Nhập PIN `1041` (hoặc `1234`/`1111`).

### 8.3. Nguyên Tắc Lập Trình Bắt Buộc (Mandatory Coding Rules)
1. **Tuyệt đối không hardcode credentials**: Mọi thông tin `DATABASE_URL`, `API_SECRET_TOKEN`, `MASTER_PIN` phải lấy từ biến môi trường `os.environ.get()`.
2. **Tránh lỗi Null JS DOM**: Trong `index.html`, khi truy vấn `document.getElementById()`, luôn kiểm tra sự tồn tại của phần tử trước khi gọi `.addEventListener()` hoặc đọc `.value` để tránh ném `TypeError` đứng màn hình đăng nhập.
3. **Transaction Safety trên Postgres**: Mọi lệnh `ALTER TABLE` hoặc Batch Update trên Postgres phải thực hiện trong khối `try...except` kèm `conn.commit()` ngay lập tức để tránh văng ngoại lệ `InFailedSqlTransaction`.
4. **Bảo tồn Phân Quyền ASM**: Khi thay đổi các API lấy số liệu hoặc xuất Excel, bắt buộc phải thông qua `get_auth_scope()` để kiểm tra đúng quyền hạn của ASM/Cửa hàng.

---
*Tài liệu này được tự động cập nhật và xác minh trực tiếp trên mã nguồn hệ thống Retail Commander Web Portal.*
