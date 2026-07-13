# Hướng Dẫn Sử Dụng Web Portal Nhập Liệu Báo Cáo Tuần (Cập Nhật 2026)

Tài liệu này hướng dẫn chi tiết quy trình đăng nhập, nhập liệu và theo dõi báo cáo trên hệ thống **An Phước QLKD Portal**.

---

## 1. Đăng Nhập Hệ Thống

Hệ thống hỗ trợ 2 vai trò đăng nhập riêng biệt để bảo mật thông tin và phân tách nhiệm vụ:

### 1.1. Dành Cho Cửa Hàng Trưởng (Store Manager)
1. Truy cập địa chỉ Web Portal.
2. Chọn **Quản lý kinh doanh phụ trách (ASM)** của cụm mình.
3. Chọn đúng tên **Cửa Hàng** từ danh sách.
4. Nhập **Mã PIN Cửa Hàng** (4 chữ số do ASM cung cấp).
5. Bấm **Vào Nhập Báo Cáo**.
*Hệ thống sẽ lưu nhớ phiên đăng nhập trên thiết bị (localStorage). Khi đăng nhập thành công, cửa hàng chỉ xem và nhập liệu được cho đơn vị mình.*

### 1.2. Dành Cho Quản Lý Kinh Doanh (ASM / Supervisor)
1. Chọn tên **Quản lý kinh doanh phụ trách (ASM)** (ví dụ: Khôi).
2. Tại dropdown Cửa Hàng, chọn dòng đầu tiên: `🔑 [Đăng nhập quyền ASM <Tên ASM>]`.
3. Nhập **Mã PIN ASM mặc định**: `9999`.
4. Bấm **Vào Nhập Báo Cáo** để chuyển hướng thẳng đến **Bảng Theo Dõi ASM (Dashboard)**.

---

## 2. Quy Trình Nhập Liệu Của Cửa Hàng

### 2.1. Nhập Số Liệu Traffic & Bill Hàng Ngày (Khuyên Dùng)
Để số liệu báo cáo tuần chính xác nhất, cửa hàng nên nhập số liệu hàng ngày tại **Tab 2: Nhập Traffic Hàng Ngày**:
1. Chọn **Năm** và **Tháng** cần nhập.
2. Tại mỗi ô ngày tương ứng trong Grid:
   * **Khách:** Nhập số lượt khách ghé cửa hàng (Traffic) thực tế trong ngày.
   * **Bill:** Nhập số lượng bill bán lẻ phát sinh thực tế trong ngày (theo POS).
3. Hệ thống sẽ tự động tính toán tỷ lệ chuyển đổi (CR) tức thời cho ngày đó:
   * **Màu Xanh (80% - 87%):** Đạt chuẩn quy định.
   * **Màu Vàng (<50% hoặc >=90%):** Cảnh báo lệch chuẩn.
   * **Màu Đỏ (>100%):** Số liệu vô lý (Số bill lớn hơn lượt khách) -> **Cần sửa lại**.
4. Bấm **Lưu Lượt Traffic Hàng Ngày**:
   * Hệ thống sẽ ngăn chặn việc lưu dữ liệu nếu phát hiện lỗi đỏ ($CR > 100\%$).
   * Hiển thị cảnh báo xác nhận nếu có ngày bị lệch chuẩn (Màu Vàng).

### 2.2. Nộp Báo Cáo Tuần (Thứ Sáu Hàng Tuần)
Báo cáo tuần chốt số liệu vào cuối ngày Thứ Sáu hàng tuần tại **Tab 1: Báo Cáo Tuần (Thứ 6)**:
1. **Ngày khóa báo cáo:** Chọn ngày Thứ Sáu của tuần báo cáo hiện tại.
2. **Traffic & Bill cả tuần:**
   * Nếu đã nhập đầy đủ hàng ngày ở Tab 2, hệ thống tự động cộng dồn và hiển thị.
   * Nếu nộp nhanh, nhập trực tiếp tổng số Traffic và Bill của cả tuần vào 2 ô tương ứng.
   * *Validation tương tự nhập ngày: Ngăn chặn nộp nếu $CR > 100\%$, cảnh báo nếu CR lệch chuẩn ($< 50\%$ hoặc $\ge 90\%$).*
3. **Phần 3.1 & 3.2 (Hợp Đồng):** Bấm thêm dòng để điền các thông tin hợp đồng phát sinh trong tuần.
4. **Phần 4.1 - 4.4 (Vận Hành & Nhân Sự):** Đánh giá hiện trạng các tiêu chuẩn và ghi nhận nhân sự/hàng hóa/thị trường.
5. **Phần 4.5 (Yêu Cầu Hỗ Trợ/Sự Cố):**
   * Nếu có sự cố kỹ thuật (POS, phần mềm, thiết bị...), bấm **+ Thêm Yêu Cầu Hỗ Trợ**.
   * Điền chi tiết sự cố, mức độ ưu tiên và hạn xử lý.
   * Khi nộp báo cáo tuần, sự cố này sẽ được **tự động đồng bộ lên Google Sheets** và **gửi email trực tiếp đến ASM & Kỹ thuật** để xử lý nhanh chóng.
6. Bấm **Nộp Báo Cáo Vận Hành Tuần** để hoàn tất.

---

## 3. Chức Năng Dành Cho ASM (Dashboard)

Khi ASM đăng nhập quyền quản lý bằng PIN `9999`:
* **Xem trạng thái nộp tuần này:** Danh sách toàn bộ các cửa hàng trong cụm với trạng thái **Đã nộp (Xanh)** hoặc **Chưa nộp (Đỏ)** cho kỳ báo cáo được chọn, kèm theo số lượng thống kê trực quan.
* **Tiến độ Traffic hàng ngày:** Bảng tổng hợp chi tiết lượt khách, số bill và tỷ lệ CR của từng cửa hàng trong tháng để ASM theo dõi sát sao tiến độ.
* **Đăng xuất an toàn:** Bấm nút **Quay Lại** ở góc phải màn hình Dashboard để đăng xuất và xóa phiên làm việc.
