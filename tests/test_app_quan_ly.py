import io
from datetime import date

import config as c
from tests.conftest import chu_tren_trang, dang_nhap, mo_app, viec, viec_cho_duyet, viec_vi_du_spec

ID = "V-00000001"
MAU = [{c.COL_ID_MAU: "M01", c.COL_TEN_VIEC: "Báo cáo tuần", c.COL_MO_TA: "Gửi trước 17h thứ Sáu", c.COL_TRONG_SO_DIEM: 2},
       {c.COL_ID_MAU: "M02", c.COL_TEN_VIEC: "Kiểm kho", c.COL_MO_TA: "", c.COL_TRONG_SO_DIEM: "abc"}]


def png_that():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), "red").save(buf, format="PNG")
    return buf.getvalue()


def vao_ql(at=None):
    return dang_nhap(at or mo_app(), "QL01", "1111")


def test_quan_ly_thay_bon_tab(app_env):
    app_env()
    at = vao_ql()
    assert not at.exception
    assert [t.label for t in at.tabs] == ["Tổng quan", "Giao việc", "Chờ duyệt", "Tất cả công việc"]


def test_nhan_vien_khong_thay_tab_quan_ly(app_env):
    app_env(tasks=[viec_cho_duyet()])
    at = dang_nhap(mo_app(), "NV01", "1234")
    khoa = [b.key for b in at.button]
    assert "gv_submit" not in khoa and f"duyet_{ID}" not in khoa and f"tra_{ID}" not in khoa


def test_vai_tro_la_khong_thay_gi(app_env):
    from tests.conftest import NHAN_SU
    app_env(tasks=[viec()], nhan_su=NHAN_SU + [{**NHAN_SU[1], c.COL_ID_NV: "X01", c.COL_SDT: "0900000009", c.COL_ROLE: "Khac"}])
    at = dang_nhap(mo_app(), "X01", "1234")
    assert not at.exception and len(at.tabs) == 0 and "Việc A" not in chu_tren_trang(at)


# --- Giao việc ---

def test_chon_mau_tu_dien(app_env):
    app_env(templates=MAU)
    at = vao_ql()
    at.selectbox(key="gv_mau").set_value("M01").run()
    assert at.text_input(key="gv_ten").value == "Báo cáo tuần"
    assert at.text_area(key="gv_mo_ta").value == "Gửi trước 17h thứ Sáu"
    assert at.number_input(key="gv_trong_so").value == 2


def test_mau_co_trong_so_hong_khong_lam_sap(app_env):          # Review Focus 1
    app_env(templates=MAU)
    at = vao_ql()
    at.selectbox(key="gv_mau").set_value("M02").run()
    assert not at.exception and at.text_input(key="gv_ten").value == "Kiểm kho"


def giao(at, ten="Báo cáo tuần", nguoi="NV01", han=date(2026, 11, 20), trong_so=3):
    at.text_input(key="gv_ten").set_value(ten)
    at.number_input(key="gv_trong_so").set_value(trong_so)
    at.selectbox(key="gv_nguoi_nhan").set_value(nguoi)
    at.date_input(key="gv_han_chot").set_value(han)
    at.button(key="gv_submit").click().run()


def test_giao_viec_tu_mau_roi_sua_mau_khong_doi_viec_cu(app_env):
    store, notifier = app_env(templates=MAU)
    at = vao_ql()
    at.selectbox(key="gv_mau").set_value("M01").run()
    at.selectbox(key="gv_nguoi_nhan").set_value("NV01")
    at.date_input(key="gv_han_chot").set_value(date(2026, 11, 20))
    at.button(key="gv_submit").click().run()
    t = store.tasks().iloc[0]
    assert (t[c.COL_TEN_VIEC], t[c.COL_MO_TA], t[c.COL_TRONG_SO]) == ("Báo cáo tuần", "Gửi trước 17h thứ Sáu", "2")
    assert at.success[0].value == c.MSG_DA_LUU and notifier.sent[0][0] == "201"
    assert at.text_input(key="gv_ten").value == ""                       # ô nhập được xóa sau khi giao
    store._spreadsheet.worksheet(c.SHEET_MAU).rows[1][3] = 5             # sửa trọng số của mẫu trên Sheet
    assert store.tasks().iloc[0][c.COL_TRONG_SO] == "2"


def test_giao_viec_thieu_ten_bao_loi_va_giu_o_nhap(app_env):
    store, _ = app_env()
    at = vao_ql()
    at.text_area(key="gv_mo_ta").set_value("mô tả đang gõ dở")
    giao(at, ten="  ")
    assert len(at.error) == 1 and len(store.tasks()) == 0
    assert at.text_area(key="gv_mo_ta").value == "mô tả đang gõ dở"
    assert at.selectbox(key="gv_nguoi_nhan").value == "NV01"


def test_giao_viec_chua_chon_nguoi_nhan_bao_loi(app_env):
    store, _ = app_env()
    at = vao_ql()
    at.text_input(key="gv_ten").set_value("Việc mới")
    at.button(key="gv_submit").click().run()
    assert len(at.error) == 1 and len(store.tasks()) == 0


def test_nguoi_nhan_chua_co_telegram_thi_canh_bao(app_env):    # Review Focus 5
    store, _ = app_env()
    at = vao_ql()
    giao(at, nguoi="NV02")
    assert at.warning[0].value == c.MSG_DA_LUU_CHUA_GUI and len(store.tasks()) == 1


# --- Chờ duyệt ---

def test_duyet_chua_chon_sao_bao_loi(app_env):
    store, _ = app_env(tasks=[viec_cho_duyet()])
    at = vao_ql()
    at.button(key=f"duyet_{ID}").click().run()
    assert len(at.error) == 1 and "sao" in at.error[0].value
    assert store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET


def test_duyet(app_env):
    store, notifier = app_env(tasks=[viec_cho_duyet()])
    at = vao_ql()
    at.radio(key=f"sao_{ID}").set_value(5)
    at.button(key=f"duyet_{ID}").click().run()
    t = store.get_task(ID)
    assert (t[c.COL_TRANG_THAI], t[c.COL_SAO], t[c.COL_DIEM]) == (c.TT_HOAN_THANH, "5", "3.24")
    assert at.success[0].value == c.MSG_DA_LUU and notifier.sent[0][0] == "201" and not at.exception


def test_tra_lai_thieu_ly_do_bao_loi(app_env):
    store, _ = app_env(tasks=[viec_cho_duyet()])
    at = vao_ql()
    at.button(key=f"tra_{ID}").click().run()
    assert len(at.error) == 1 and "lý do" in at.error[0].value
    assert store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_CHO_DUYET


def test_tra_lai(app_env):
    store, _ = app_env(tasks=[viec_cho_duyet()])
    at = vao_ql()
    at.text_input(key=f"ly_do_{ID}").set_value("Thiếu số liệu")
    at.button(key=f"tra_{ID}").click().run()
    t = store.get_task(ID)
    assert (t[c.COL_TRANG_THAI], t[c.COL_GHI_CHU_QL]) == (c.TT_LAM_LAI, "Thiếu số liệu")


def test_chung_minh_link_bam_duoc(app_env):
    app_env(tasks=[viec_cho_duyet()])
    at = vao_ql()
    assert any("](<https://a.vn>)" in m.value for m in at.markdown)


def test_chung_minh_khong_phai_link_thi_khong_thanh_link(app_env):
    app_env(tasks=[viec_cho_duyet(Link_Chung_Minh="javascript:alert(1)")])   # ô bị sửa tay trên Sheet
    at = vao_ql()
    assert not any("javascript:" in m.value for m in at.markdown)
    assert any("javascript:alert(1)" in k.value for k in at.code)


def test_chung_minh_anh_hien_bang_bytes_khong_lo_token(app_env):
    _, notifier = app_env(tasks=[viec_cho_duyet(Link_Chung_Minh="tg:FILE123")])
    notifier.photo_bytes = png_that()
    at = vao_ql()
    assert not at.exception and len(at.get("image")) == 1
    toan_bo = str(at.get("image")[0].proto) + chu_tren_trang(at)
    assert "api.telegram.org" not in toan_bo and "token-gia" not in toan_bo


def test_anh_tai_khong_duoc_thi_bao_va_van_duyet_duoc(app_env):
    store, notifier = app_env(tasks=[viec_cho_duyet(Link_Chung_Minh="tg:FILE123")])
    at = vao_ql()                                   # fetch_photo trả None
    assert not at.exception and any("ảnh" in w.value for w in at.warning)
    at.radio(key=f"sao_{ID}").set_value(4)
    at.button(key=f"duyet_{ID}").click().run()
    assert store.get_task(ID)[c.COL_TRANG_THAI] == c.TT_HOAN_THANH


def test_khong_co_viec_cho_duyet(app_env):
    app_env(tasks=[viec()])
    at = vao_ql()
    assert "Không có việc nào đang chờ duyệt" in chu_tren_trang(at)


# --- Tổng quan và Tất cả công việc ---

def test_tong_quan(app_env):
    qua_han = viec(ID_Viec="V-00000009", Ten_Viec="Việc trễ", Nguoi_Nhan="NV02", Han_Chot="2026-11-05")
    app_env(tasks=viec_vi_du_spec(da_duyet=True) + [qua_han])
    at = vao_ql()
    assert at.selectbox(key="tq_quy").value == "2026-Q4"
    assert {m.label: m.value for m in at.metric} == {
        c.TT_MOI_GIAO: "1", c.TT_DANG_LAM: "1", c.TT_CHO_DUYET: "0", c.TT_HOAN_THANH: "3", c.TT_LAM_LAI: "0"}
    bang_kpi = at.dataframe[0].value.astype(str)
    dong_nv1 = " ".join(bang_kpi.iloc[0])
    assert "Nguyễn An" in dong_nv1 and "49.57" in dong_nv1 and "3/4" in dong_nv1
    assert "0/1" in " ".join(bang_kpi.iloc[1])
    bang_qua_han = at.dataframe[1].value.astype(str)
    assert list(bang_qua_han.iloc[:, 0]) == ["Việc trễ"]


def test_tong_quan_nhan_vien_chua_co_viec(app_env):
    app_env(tasks=viec_vi_du_spec(da_duyet=True))
    at = vao_ql()
    assert "Chưa có việc" in " ".join(at.dataframe[0].value.astype(str).iloc[1])
    assert "Không có việc quá hạn" in chu_tren_trang(at)


def test_bang_trong_khong_sap(app_env):
    app_env()
    at = vao_ql()
    assert not at.exception


def test_o_ngay_hong_tren_sheet_khong_sap(app_env):            # Review Focus 1
    app_env(tasks=[viec(Han_Chot="20/11/2026", Trong_So="", Quy=""), viec_cho_duyet(ID_Viec="V-00000002", Ngay_Hoan_Thanh="")])
    at = vao_ql()
    assert not at.exception
    at.radio(key="sao_V-00000002").set_value(4)
    at.button(key="duyet_V-00000002").click().run()
    assert not at.exception and c.COL_NGAY_HOAN_THANH in at.error[0].value


def test_loc_tat_ca_cong_viec(app_env):
    app_env(tasks=[viec(), viec(ID_Viec="V-00000002", Ten_Viec="Việc B", Nguoi_Nhan="NV02", Trang_Thai=c.TT_DANG_LAM)])
    at = vao_ql()
    assert len(at.dataframe[-1].value) == 2
    at.selectbox(key="all_nv").set_value("NV02").run()
    assert list(at.dataframe[-1].value[c.COL_TEN_VIEC]) == ["Việc B"]
    at.selectbox(key="all_tt").set_value(c.TT_MOI_GIAO).run()
    assert len(at.dataframe[-1].value) == 0
