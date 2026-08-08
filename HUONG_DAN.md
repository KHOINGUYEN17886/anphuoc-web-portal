# Hướng Dẫn Sử Dụng Web Portal Nhập Liệu & Báo Cáo Vận Hành QLKD (Cập Nhật 08/2026)

Tài liệu này hướng dẫn chi tiết quy trình đăng nhập, nhập liệu traffic, nộp báo cáo vận hành tuần, quản lý sự vụ tuân thủ P.QLQT, theo dõi định biên nhân sự và sử dụng các tính năng mới được đồng nghiệp phát triển trên hệ thống **An Phước Retail Commander Web Portal**.

---

## 1. Đăng Nhập Hệ Thống & Phân Quyền Bảo Mật

Hệ thống phân tách 3 vai trò người dùng chính với cơ chế bảo mật cô lập dữ liệu (Strict Role-Based Scoping):

### 1.1. Dành Cho Cửa Hàng Trưởng (Store Manager)
1. Truy cập Web Portal: `https://anphuoc-portal.onrender.com`
2. Chọn **Quản lý kinh doanh phụ trách (ASM)** của cụm mình.
3. Chọn đúng tên **Cửa Hàng** từ danh sách (Danh sách 184 cửa hàng tự động lọc theo ASM đã chọn).
4. Nhập **Mã PIN Cửa Hàng** (4 chữ số do ASM cung cấp hoặc mặc định `1234`).
5. Bấm **Vào Nhập Báo Cáo**.
   * *Hệ thống tự động lưu phiên đăng nhập trên thiết bị (`localStorage`). Cửa hàng được bảo mật cô lập tuyệt đối, chỉ xem và thao tác dữ liệu đúng của Cửa hàng mình, không truy cập được cửa hàng khác.*

### 1.2. Dành Cho Quản Lý Kinh Doanh (ASM / Supervisor)
1. Chọn tên **Quản lý kinh doanh phụ trách (ASM)** (ví dụ: Khôi, Dũng, Linh, Tiên, Hương, Lâm, Quân, Ni, Thắng...).
2. Tại dropdown Cửa Hàng, chọn dòng đầu tiên: `🔑 [Đăng nhập quyền ASM <Tên ASM>]`.
3. Nhập **Mã PIN ASM** (Mặc định `9999` hoặc PIN cá nhân).
4. Bấm **Vào Nhập Báo Cáo** để chuyển hướng thẳng đến **Bảng Theo Dõi ASM (Dashboard)**.
   * *ASM được phân quyền quản lý toàn bộ các cửa hàng trong cụm trực tiếp phụ trách, xem báo cáo tổng hợp, đánh giá giải trình sự vụ tuân thủ và xuất file Excel theo cụm.*

### 1.3. Dành Cho Ban Giám Đốc & Admin (Executive Management)
1. Đăng nhập với quyền **Admin / Quản Trị Viên** (Nhập PIN Admin hoặc Master PIN `8888`).
2. Admin có toàn quyền xem và điều hành **184 cửa hàng toàn quốc**, xuất file Excel Toàn Quốc, xem Bản đồ GIS Vận hành và điều chỉnh phân cụm ASM quản lý cửa hàng động.

---

## 2. Quy Trình Nhập Traffic & Báo Cáo Dành Cho Cửa Hàng

### 2.1. Nhập Số Liệu Traffic & Hóa Đơn Hàng Ngày (Tab 2)
Cửa hàng nên nhập số liệu hàng ngày tại **Tab 2: Nhập Traffic Hàng Ngày** để dữ liệu báo cáo tuần tự động chính xác:
1. Chọn **Năm** và **Tháng** cần nhập.
2. Tại mỗi ô ngày trong tháng:
   * **Khách:** Nhập lượt khách ghé cửa hàng (Footfall thực tế theo camera/ghi nhận).
   * **Bill:** Nhập tổng số lượng hóa đơn bán lẻ phát sinh thực tế tại cửa hàng (theo POS).
   * **OL C.ty:** Số lượng bill online do Công ty đẩy về cửa hàng đóng gói (nếu có).
   * **OL CH:** Số lượng bill online do Cửa hàng tự chốt bán (nếu có).
3. **Công thức Tỷ lệ Chuyển đổi CR % tại quầy**:
   $$\text{CR \%} = \frac{\text{Bill bán lẻ} - \text{Bill Online C.ty}}{\text{Lượt khách}} \times 100\%$$
   * **Màu Xanh (80% - 87%):** Đạt chuẩn quy định.
   * **Màu Vàng (<50% hoặc >=90%):** Cảnh báo lệch chuẩn.
   * **Màu Đỏ (>100%):** Số bill lớn hơn lượt khách.
4. **Quy tắc Lưu Số Liệu Mới (In-Page Banner & Modal Phản Hồi 100%)**:
   * Khi bấm **`💾 LƯU SỐ LIỆU TRAFFIC CẢ THÁNG`**:
     - Nếu có ngày CR > 100% (do camera đếm thiếu hoặc khách mua nhiều bill), hệ thống hiển thị **In-Page Banner Cảnh Báo & Modal Xác Nhận** thông minh, không bị trình duyệt chặn popup.
     - Cửa hàng chỉ cần bấm **Xác Nhận Lưu**, dữ liệu lập tức được gửi và lưu 100% lên Database.
     - Đèn trạng thái hiển thị banner xanh khẳng định: `✅ ĐÃ LƯU THÀNH CÔNG SỐ LIỆU TRAFFIC THÁNG!`.
5. **Ghi Nhận Lý Do Khách Không Mua**:
   * Bấm nút `🏷️ Lý do` tại từng ngày để tích chọn nguyên nhân chính (📏 Đứt size, 🎨 Mẫu mã, 💵 Giá/KM, 👔 Chỉ xem, 🏬 Hàng mới, ⏳ Phục vụ) và nhập Ghi chú chi tiết.

### 2.2. Nộp Báo Cáo Vận Hành Tuần (Tab 1 - Thứ Sáu Hàng Tuần)
Báo cáo tuần chốt số liệu vào cuối ngày Thứ Sáu hàng tuần:
1. **Ngày khóa báo cáo:** Chọn ngày Thứ Sáu của tuần báo cáo hiện tại.
2. **Traffic & Bill cả tuần:** Tự động cộng dồn từ Tab 2 hoặc nhập trực tiếp tổng số của tuần.
3. **Phần 3.1 & 3.2 (Hợp Đồng B2B):**
   * Điền chi tiết hợp đồng phát sinh trong tuần (Mục 3.1).
   * Điền hợp đồng cùng kỳ năm trước chưa ký lại (Mục 3.2), bắt buộc có **Tên Khách Hàng / Doanh nghiệp**.
4. **Phần 4.1 - 4.4 (Vận Hành & Nhân Sự):** Đánh giá mở/đóng cửa, đồng phục, câu chào, thái độ và thông tin thị trường/hàng hóa.
5. **Phần 4.5 (Yêu Cầu Hỗ Trợ / Sự Cố Vận Hành):**
   * Bấm **+ Thêm Yêu Cầu Hỗ Trợ** nếu có sự cố CNTT, POS, thiết bị, cơ sở vật chất.
   * Chọn phân loại, mức độ ưu tiên (Khẩn cấp, Cao, Trung bình, Thấp) và hạn xử lý.
   * Hệ thống quản lý tương tác 8 cột cho phép ASM & Kỹ thuật xem và cập nhật tiến độ xử lý trực tiếp.
6. Bấm **Nộp Báo Cáo Vận Hành Tuần** để hoàn tất.

---

## 3. Module P.QLQT Sự Vụ Tuân Thủ & Đính Kèm Tờ Trình (Tab 3)

Hệ thống tích hợp quy trình kiểm soát sự vụ tuân thủ và giải trình minh bạch 3 bên (Cửa Hàng ↔ ASM ↔ P.QLQT):

### 3.1. Dành Cho Cửa Hàng Trưởng
1. Vào **Tab 3: Sự Vụ Tuân Thủ (P.QLQT)** để xem danh sách các vi phạm/sự vụ tuân thủ được ghi nhận.
2. Xem chi tiết vị trí vi phạm, mức phạt chức danh (CHT / CHP / NVBH) và số tiền trừ thưởng theo tháng.
3. Nếu cần giải trình:
   * Bấm nút **`📝 Cửa Hàng Giải Trình`**.
   * Nhập nội dung giải trình chi tiết.
   * **Đính kèm Tờ Trình / Hồ sơ minh chứng:** Tải lên file tờ trình (PDF, DOCX, PNG, JPG). File được lưu trữ an toàn trực tiếp trong Database Cloud (`tb_compliance_attachments`), đảm bảo 100% không bao giờ bị mất hay lỗi 404.
   * Bấm **Gửi Giải Trình**. Trạng thái chuyển sang `CH đã giải trình` và tự động gửi thông báo đến ASM.

### 3.2. Dành Cho ASM & Admin
1. ASM mở Tab Sự Vụ Tuân Thủ Cụm hoặc bấm nút **`⚖️ Đánh Giá Sự Vụ`** trên bảng.
2. Trong Modal đánh giá của ASM:
   * Đọc trực tiếp **Nội dung Cửa Hàng đã giải trình**.
   * Bấm nút **`👁️ Xem / Tải Tờ Trình`** để mở hoặc tải file đính kèm của cửa hàng ngay trong trình duyệt.
   * Chọn Trạng thái đánh giá:
     - **`Hoàn tất`**: Đồng ý với giải trình của Cửa hàng. Nút chuyển sang màu Xanh Emerald.
     - **`Yêu cầu giải trình lại`**: Yêu cầu Cửa hàng bổ sung thông tin. Nút chuyển sang màu Hổ Phách (Amber).
   * Nhập Ghi chú đánh giá của ASM và bấm **Lưu Đánh Giá ASM**.
3. **Xuất Excel Báo Cáo Tuân Thủ**: Bấm nút `📊 Xuất Excel Tuân Thủ` để tải báo cáo chi tiết kèm mức phạt theo phân quyền.

---

## 4. Module Định Biên & Báo Cáo Nhân Sự Nâng Cấp (Tab 4)

Hệ thống tích hợp các tính năng quản lý nhân sự nâng cao được phát triển mới:

### 4.1. Bảng Hồ Sơ Nhân Sự 6 Cột Cân Đối & Sắp Xếp Tự Động
* Bảng hiển thị 6 cột: Mã NV, Ảnh chân dung, Họ tên, Chức danh, Thâm niên, Trạng thái/Ghi chú.
* **Thuật toán sắp xếp thông minh**: Tự động đưa Chức danh chủ chốt lên đầu (Cửa hàng trưởng ➔ Cửa hàng phó ➔ Nhân viên bán hàng ➔ Nhân viên thử việc), sau đó ưu tiên theo Thâm niên công tác.

### 4.2. Xây Dựng Profile Chi Tiết & Tải Ảnh Trực Tiếp Từ Điện Thoại / Máy Tính
* **Xem Profile Đầy Đủ**: Bấm vào Họ tên nhân viên bất kỳ để mở **Popup Hồ Sơ Nhân Viên**.
* **Ảnh Chân Dung Lớn (1/4 Popup)**: Popup hiển thị ảnh chân dung rõ nét chiếm 1/4 diện tích khung hình.
* **Tải Ảnh Trực Tiếp & Nén Tự Động**: Hỗ trợ chọn ảnh từ điện thoại/máy tính để tải lên. Hệ thống tự động nạp công cụ nén ảnh (Client-side compression) giúp giảm dung lượng ảnh mà vẫn giữ độ nét cao, tiết kiệm băng thông.
* **Lịch Sử Điều Chuyển & Ghi Chú Nâng Cao**: Xem và cập nhật chi tiết lịch sử chuyển cửa hàng, quá trình khen thưởng, kỷ luật, kỹ năng và đánh giá năng lực nhân viên.

### 4.3. Quy Tắc Định Biên Headcount Mới (Tự Động Loại Trừ Bảo Vệ)
* **Quy tắc trừ Bảo vệ**: Nhân sự có chức danh **Bảo vệ** sẽ tự động được **loại trừ khỏi chỉ tiêu định biên bán hàng** (Headcount quota) của cửa hàng, giúp tính toán chính xác số lượng nhân viên bán hàng thực tế thiếu/đủ.
* **Live Update Summary Chips**: Các thẻ thống kê tổng quan (Tổng nhân sự, Thiếu/Đủ định biên, Số thử việc) tự động cập nhật thời gian thực khi có thay đổi.

### 4.4. Quản Lý Thử Việc 5 Bài Học & Biến Động Nhân Sự
* **Đào tạo thử việc**: Đánh giá 5 bài học đào tạo và cập nhật kết quả (`Đang thử việc`, `Đạt - Ký HDLD`, `Không đạt - Cho nghỉ`).
* **Sự vụ biến động**: Tạo và duyệt ticket Tuyển mới, Nghỉ việc, Thai sản, Điều chuyển kèm trạng thái bàn giao công việc.

---

## 5. Chức Năng Dành Cho ASM & Admin (Dashboard & System Controls)

### 5.1. Dashboard ASM & Dynamic Store Dropdown
* **Trạng Thái Nộp Tuần:** Danh sách 184 cửa hàng với trạng thái **Đã nộp (Xanh)** hoặc **Chưa nộp (Đỏ)** cho kỳ báo cáo Thứ 6 được chọn.
* **Lọc Theo Cụm ASM Tự Động:** ASM chỉ thấy danh sách cửa hàng thuộc cụm mình phụ trách (Riêng Admin và ASM Khôi được xem toàn quốc hoặc chọn lọc từng ASM).
* **Đăng Xuất An Toàn:** Bấm nút **Quay Lại / Đăng Xuất** ở góc trên màn hình để xóa phiên làm việc khỏi thiết bị.

### 5.2. Chuyển Đổi ASM Quản Lý Cửa Hàng Động (Dành Cho Admin)
* Admin có quyền thay đổi ASM phụ trách cho bất kỳ cửa hàng nào trực tiếp qua dropdown trên bảng quản lý cửa hàng.
* Sau khi đổi, hệ thống lưu tức thì lên Cloud Server qua API `/api/admin/update_store_asm`, tự động đồng bộ danh sách 184 cửa hàng mà không cần khởi động lại máy chủ.

### 5.3. Bản Đồ GIS Vận Hành Mạng Lưới Cửa Hàng (`/map`)
* Đăng nhập quyền Admin/ASM ➔ Bấm nút **`🗺️ Bản Đồ GIS Cửa Hàng`** trên thanh công cụ.
* Bản đồ hiển thị tọa độ 184 cửa hàng toàn quốc kèm các chỉ số vận hành thực tế (Traffic, Bill POS, Tỷ lệ CR %, Số hợp đồng B2B, Số nhân sự active).
* *Quyền hạn: Tính năng này bị khóa hoàn toàn đối với tài khoản Cửa Hàng.*

### 5.4. Xuất Báo Cáo Excel 11 Sheets Với Tên File Động
* Bấm nút **`📊 Xuất Báo Cáo Excel`** trên Header hoặc Admin Control Bar.
* Hệ thống tự động tạo file Excel 11 Sheets chuẩn doanh nghiệp với tone màu Navy chuyên nghiệp.
* **Tên file động thông minh theo Scope (Phân quyền)**:
  - Cửa Hàng: `BaoCao_RetailCommander_CH_126_3T2_2026-08-08.xlsx`
  - ASM: `BaoCao_RetailCommander_ASM_Khoi_2026-08-08.xlsx`, `BaoCao_RetailCommander_ASM_Dung_2026-08-08.xlsx`
  - Admin (Toàn Quốc): `BaoCao_RetailCommander_ToanQuoc_2026-08-08.xlsx`

---

## 6. Hướng Dẫn Xử Lý Tình Huống Bất Thường (Troubleshooting FAQ)

| Tình Huống | Nguyên Nhân | Cách Xử Lý |
| :--- | :--- | :--- |
| **Bấm "Lưu Số Liệu Traffic" hiện banner Cảnh Báo CR > 100%** | Số bill vượt lượt khách (do camera đếm thiếu hoặc khách mua nhiều bill) | Đọc danh sách các ngày cảnh báo trong banner/modal, bấm **Xác Nhận Lưu** để lưu dữ liệu 100% thành công lên máy chủ. |
| **Bảo vệ có tính vào định biên headcount không?** | Quy tắc hệ thống mới | Bảo vệ tự động được loại trừ khỏi chỉ tiêu định biên bán hàng để tính đúng lực lượng bán lẻ thực tế. |
| **Ảnh chân dung nhân viên tải lên bị mờ hoặc nặng** | Ảnh gốc từ camera điện thoại | Hệ thống tự động nén dung lượng client-side giúp ảnh load nhanh và giữ nét 100%. |
| **Không tải được file Tờ Trình đính kèm** | File vừa được tải lên hoặc đường truyền chậm | Bấm lại nút `👁️ Xem / Tải Tờ Trình`. Tờ trình đã lưu trữ vĩnh viễn trong Database Cloud. |
| **Tài khoản Cửa Hàng không thấy nút Đánh Giá ASM** | Phân quyền bảo mật (RBAC) | Quyền Đánh giá sự vụ tuân thủ chỉ dành riêng cho ASM và Admin. Cửa hàng chỉ thực hiện Giải trình và Đính kèm Tờ trình. |

---
*Bản quyền tài liệu thuộc về Hệ Thống Quản Lý Vận Hành An Phước Retail Commander.*
