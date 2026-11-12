import config as c
from tests.conftest import NHAN_SU, chu_tren_trang, dang_nhap, html_tren_trang, mo_app, viec, viec_vi_du_spec

# "Hôm nay" trong app_env là 2026-11-11
VIEC = [
    viec(ID_Viec="V-1", Ten_Viec="Việc của An tháng 11", Han_Chot="2026-11-20", Trang_Thai=c.TT_DANG_LAM),
    viec(ID_Viec="V-2", Ten_Viec="Việc của Bình quá hạn", Han_Chot="2026-11-05", Nguoi_Nhan="NV02"),
    viec(ID_Viec="V-3", Ten_Viec="Việc của An tháng 12", Han_Chot="2026-12-03"),
    viec(ID_Viec="V-4", Ten_Viec="Việc quý sau", Han_Chot="2027-01-10"),
]


def nut_lich(at):
    """Nhãn các việc đang hiện trên lịch (mỗi việc là một nút bấm được)."""
    return {b.key: b.label for b in at.button if (b.key or "").startswith("lv_")}


def test_quan_ly_thay_lich_thang_hien_tai_kem_ten_nguoi(app_env):
    app_env(tasks=VIEC)
    at = dang_nhap(mo_app(), "QL01", "1111")
    assert not at.exception
    nut = nut_lich(at)
    assert nut[f"lv_{c.NHOM_DANG_LAM}_V-1"] == "Việc của An tháng 11 · Nguyễn An"
    assert nut[f"lv_{c.NHOM_QUA_HAN}_V-2"] == "Việc của Bình quá hạn · Lê Bình"
    assert len(nut) == 2                                     # việc tháng 12 và quý sau chưa hiện
    assert any("Tháng 11/2026" in s.value for s in at.subheader)
    assert 'class="gv-chu-giai"' in html_tren_trang(at)


def test_chuyen_thang(app_env):
    app_env(tasks=VIEC)
    at = dang_nhap(mo_app(), "QL01", "1111")
    at.button(key="lich_sau").click().run()
    assert list(nut_lich(at)) == [f"lv_{c.NHOM_DANG_LAM}_V-3"] and any("Tháng 12/2026" in s.value for s in at.subheader)
    at.button(key="lich_sau").click().run()
    assert list(nut_lich(at)) == [f"lv_{c.NHOM_DANG_LAM}_V-4"] and any("Tháng 1/2027" in s.value for s in at.subheader)
    at.button(key="lich_hom_nay").click().run()
    assert any("Tháng 11/2026" in s.value for s in at.subheader)
    at.button(key="lich_truoc").click().run()
    assert any("Tháng 10/2026" in s.value for s in at.subheader) and not at.exception and nut_lich(at) == {}


def test_bam_vao_viec_tren_lich_thi_thay_chi_tiet(app_env):
    app_env(tasks=[viec(ID_Viec="V-9", Ten_Viec="Sửa báo giá", Mo_Ta="Bổ sung số liệu", Han_Chot="2026-11-20",
                        Trang_Thai=c.TT_LAM_LAI, Ghi_Chu_QL="Thiếu số liệu tháng 10", Trong_So="4",
                        Link_Chung_Minh="https://a.vn/bao-gia", Ngay_Hoan_Thanh="2026-11-09")])
    at = dang_nhap(mo_app(), "QL01", "1111")
    assert "Thiếu số liệu tháng 10" not in chu_tren_trang(at)            # chưa bấm thì chưa hiện chi tiết
    at.button(key=f"lv_{c.NHOM_DANG_LAM}_V-9").click().run()
    assert not at.exception
    chu = chu_tren_trang(at)
    for can_co in ["Sửa báo giá", "Bổ sung số liệu", "Nguyễn An", c.TT_LAM_LAI, "2026-11-20", "Thiếu số liệu tháng 10", "https://a.vn/bao-gia"]:
        assert can_co in chu, can_co


def test_ngay_nhieu_viec_thi_gom_lai_va_bam_xem_duoc_het(app_env):
    app_env(tasks=[viec(ID_Viec=f"V-{i}", Ten_Viec=f"Việc số {i}", Han_Chot="2026-11-20") for i in range(6)])
    at = dang_nhap(mo_app(), "QL01", "1111")
    assert len(nut_lich(at)) == 3
    them = at.button(key="lvthem_2026-11-20")
    assert them.label == "+3 mục khác"
    them.click().run()
    chu = chu_tren_trang(at)
    assert not at.exception and all(f"Việc số {i}" in chu for i in range(6))


def test_ten_viec_co_ky_tu_markdown_duoc_escape_tren_nut(app_env):
    app_env(tasks=[viec(ID_Viec="V-1", Ten_Viec="[bấm](http://xau.vn) **đậm**", Han_Chot="2026-11-20")])
    at = dang_nhap(mo_app(), "NV01", "1234")
    nhan = nut_lich(at)[f"lv_{c.NHOM_DANG_LAM}_V-1"]
    assert "[bấm](" not in nhan and "**đậm**" not in nhan and "bấm" in nhan


def test_the_so_lieu_theo_quy_dang_chon(app_env):
    app_env(tasks=VIEC)
    at = dang_nhap(mo_app(), "QL01", "1111")
    the = html_tren_trang(at)
    assert f'<div class="gv-nhan">Đang thực hiện</div><div class="gv-so">2</div>' in the      # V-1, V-3 (quý 4)
    assert f'<div class="gv-nhan">Quá hạn</div><div class="gv-so">1</div>' in the
    at.selectbox(key="tq_quy").set_value("2027-Q1").run()
    assert f'<div class="gv-nhan">Đang thực hiện</div><div class="gv-so">1</div>' in html_tren_trang(at)


def test_co_hai_bieu_do(app_env):
    app_env(tasks=viec_vi_du_spec(da_duyet=True))
    at = dang_nhap(mo_app(), "QL01", "1111")
    assert not at.exception and len(at.get("vega_lite_chart")) >= 2


def test_bang_trong_khong_sap_va_van_co_lich(app_env):
    app_env()
    at = dang_nhap(mo_app(), "QL01", "1111")
    assert not at.exception and any("Lịch làm việc" in x.value for x in at.subheader) and nut_lich(at) == {}


def test_nhan_vien_chi_thay_viec_cua_minh_tren_lich_va_the(app_env):
    app_env(tasks=VIEC)
    at = dang_nhap(mo_app(), "NV01", "1234")
    assert not at.exception
    assert nut_lich(at) == {f"lv_{c.NHOM_DANG_LAM}_V-1": "Việc của An tháng 11"}     # không ghi tên người nhận
    trang = html_tren_trang(at)
    assert f'<div class="gv-nhan">Đang thực hiện</div><div class="gv-so">3</div>' in trang
    assert f'<div class="gv-nhan">Quá hạn</div><div class="gv-so">0</div>' in trang
    assert "Việc của Bình quá hạn" not in chu_tren_trang(at)


def test_ten_viec_co_the_html_khong_lot_ra_trang(app_env):
    app_env(tasks=[viec(Ten_Viec="<img src=x onerror=alert(1)>", Han_Chot="2026-11-20", Trang_Thai=c.TT_CHO_DUYET)])
    at = dang_nhap(mo_app(), "QL01", "1111")
    assert not at.exception and "<img" not in html_tren_trang(at)


# --- Khối "Việc cần xử lý" ---

def test_quan_ly_thay_viec_can_xu_ly(app_env):
    app_env(tasks=[viec(ID_Viec="V-1", Ten_Viec="Hợp đồng mẫu", Trang_Thai=c.TT_CHO_DUYET, Nguoi_Nhan="NV02"),
                   viec(ID_Viec="V-2", Ten_Viec="Bảng giá", Trang_Thai=c.TT_DANG_LAM, Han_Chot="2026-11-05"),
                   viec(ID_Viec="V-3", Ten_Viec="Việc thong thả", Trang_Thai=c.TT_DANG_LAM, Han_Chot="2026-11-30")])
    at = dang_nhap(mo_app(), "QL01", "1111")
    khoi = [e for e in at.expander if "Việc cần xử lý" in e.label]
    assert len(khoi) == 1 and "(2)" in khoi[0].label
    chu = " | ".join(m.value for m in khoi[0].markdown)
    assert "Hợp đồng mẫu" in chu and "Lê Bình" in chu and "Bảng giá" in chu and "2026-11-05" in chu
    assert c.CXL_NHAN[c.CXL_CHO_DUYET] in chu and c.CXL_NHAN[c.CXL_QUA_HAN] in chu
    assert "Việc thong thả" not in chu
    assert any("2 việc cần xử lý" in x.value for x in at.sidebar.markdown)


def test_nhan_vien_thay_viec_can_xu_ly_cua_minh_kem_ly_do(app_env):
    app_env(tasks=[viec(ID_Viec="V-1", Ten_Viec="Sửa báo giá", Trang_Thai=c.TT_LAM_LAI, Ghi_Chu_QL="Thiếu số liệu", Han_Chot="2026-11-30"),
                   viec(ID_Viec="V-2", Ten_Viec="Việc của Bình", Trang_Thai=c.TT_MOI_GIAO, Nguoi_Nhan="NV02")])
    at = dang_nhap(mo_app(), "NV01", "1234")
    khoi = [e for e in at.expander if "Việc cần xử lý" in e.label][0]
    chu = " | ".join(m.value for m in khoi.markdown)
    assert "(1)" in khoi.label and "Sửa báo giá" in chu and "Thiếu số liệu" in chu and "Việc của Bình" not in chu


def test_khong_co_viec_can_xu_ly(app_env):
    app_env(tasks=[viec(Trang_Thai=c.TT_HOAN_THANH)])
    at = dang_nhap(mo_app(), "QL01", "1111")
    assert not [e for e in at.expander if "Việc cần xử lý" in e.label]
    assert "Không có việc nào cần xử lý" in chu_tren_trang(at)
