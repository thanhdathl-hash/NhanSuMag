"""Các khối giao diện tự dựng bằng HTML: thẻ số liệu và lịch hạn chót.

Chỉ gồm hàm thuần trả về chuỗi HTML. Mọi chữ lấy từ Sheet đều qua html.escape.
"""
import calendar
import html
from datetime import date

import config

SO_VIEC_MOI_O = 3   # số việc tối đa hiện trong một ô ngày; phần còn lại gom thành "+n việc khác"

# Màu của bốn nhóm việc, dùng chung cho thẻ, biểu đồ và lịch: (màu chính, màu nền nhạt, biểu tượng)
MAU_NHOM = {
    config.NHOM_DANG_LAM: ("#1e9bf0", "#e8f4fe", "▶"),
    config.NHOM_CHO_DUYET: ("#e6a700", "#fff6dd", "⏳"),
    config.NHOM_QUA_HAN: ("#f04438", "#feeceb", "⛔"),
    config.NHOM_HOAN_THANH: ("#12b76a", "#e6f8ef", "✔"),
}
NEN_KHOI = "#ffffff"   # nền của các khối trắng trên trang
THU = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]


def _css_nhom() -> str:
    return "".join(
        f'[class*="st-key-lv_{n}_"] button{{background:{nen};border-left:3px solid {mau}}}'
        f'[class*="st-key-lv_{n}_"] button:hover{{background:{nen};border-left:3px solid {mau};filter:brightness(.96)}}'
        for n, (mau, nen, _) in MAU_NHOM.items()) + "".join(
        f".gv-the.gv-{n} .gv-so{{color:{mau}}}.gv-the.gv-{n} .gv-bieu-tuong{{background:{nen};color:{mau}}}"
        f".gv-cham.gv-{n}{{background:{mau}}}"
        for n, (mau, nen, _) in MAU_NHOM.items())


CSS = """<style>
.gv-hang-the{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin:4px 0 12px}
.gv-the{background:#fff;border:1px solid #e6e9f0;border-radius:12px;padding:16px 18px;display:flex;align-items:center;gap:14px;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.gv-bieu-tuong{width:46px;height:46px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;flex:none}
.gv-nhan{color:#475467;font-size:14px}
.gv-so{font-size:34px;font-weight:700;line-height:1.1}
.gv-so-ngay{display:inline-block;min-width:24px;height:24px;line-height:24px;text-align:center;color:#344054;font-weight:600;font-size:13px;margin-bottom:2px}
.gv-chu-giai{display:flex;gap:18px;flex-wrap:wrap;margin:8px 2px 0;color:#475467;font-size:13px}
.gv-cham{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
/* khối có viền của Streamlit (biểu đồ, thẻ việc) nền trắng trên nền xám của trang */
[class*="st-key-khoi_"]{background:#fff}
/* Lịch bấm được: lưới 7 cột bằng cột của Streamlit, mỗi việc là một nút */
.gv-thu{color:#475467;font-weight:600;font-size:13px;padding:0 4px}
.st-key-luoi_lich{gap:6px}
.st-key-luoi_lich [data-testid="stHorizontalBlock"]{flex-wrap:nowrap;gap:6px}
.st-key-luoi_lich [data-testid="stColumn"]{min-width:0;flex:1 1 0}
[class*="st-key-lichngay_"],[class*="st-key-lichnay_"],[class*="st-key-lichngoai_"]{background:#fff;border:1px solid #e6e9f0;border-radius:8px;padding:4px 6px 6px;min-height:108px;gap:3px}
[class*="st-key-lichngoai_"]{background:#fafbfd}[class*="st-key-lichngoai_"] .gv-so-ngay{color:#c0c6d4}
[class*="st-key-lichnay_"]{border-color:#5b5fe9}
[class*="st-key-lichnay_"] .gv-so-ngay{background:#5b5fe9;color:#fff;border-radius:50%}
[class*="st-key-lv_"] button,[class*="st-key-lvthem_"] button{min-height:0;padding:2px 6px;border:none;border-radius:4px;justify-content:flex-start;text-align:left;color:#1f2937}
[class*="st-key-lv_"] button p,[class*="st-key-lvthem_"] button p{font-size:12.5px;line-height:1.3;text-align:left;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
[class*="st-key-lvthem_"] button{background:transparent;color:#667085}
.st-key-khoi_can_xu_ly ul{margin:0 0 6px}
@media (max-width:900px){.gv-hang-the{grid-template-columns:repeat(2,minmax(0,1fr))}}
""" + _css_nhom() + "</style>"


_MD_DAC_BIET = "\\`*_[]()~$<>#|"


def md_escape(s: str) -> str:
    """Vô hiệu ký tự Markdown trong chữ lấy từ Sheet trước khi đưa vào nhãn nút hay st.markdown."""
    return "".join("\\" + ch if ch in _MD_DAC_BIET else ch for ch in str(s)).replace("\n", " ")


def month_weeks(year: int, month: int) -> list[list[date]]:
    """Các tuần (thứ Hai đến Chủ nhật) phủ kín một tháng."""
    return calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)


def stat_cards_html(counts: dict[str, int]) -> str:
    """Hàng bốn thẻ số liệu theo config.NHOM_VIEC."""
    the = []
    for nhom in config.NHOM_VIEC:
        the.append(
            f'<div class="gv-the gv-{nhom}"><div class="gv-bieu-tuong">{MAU_NHOM[nhom][2]}</div>'
            f'<div><div class="gv-nhan">{html.escape(config.NHOM_NHAN[nhom])}</div>'
            f'<div class="gv-so">{int(counts.get(nhom, 0))}</div></div></div>')
    return f'<div class="gv-hang-the">{"".join(the)}</div>'


def legend_html() -> str:
    """Chú giải màu của bốn nhóm việc."""
    muc = "".join(f'<span><span class="gv-cham gv-{n}"></span>{html.escape(config.NHOM_NHAN[n])}</span>'
                  for n in config.NHOM_VIEC)
    return f'<div class="gv-chu-giai">{muc}</div>'


# --- Biểu đồ (Altair, đi kèm Streamlit) ---

MAU_TRANG_THAI = {
    config.TT_MOI_GIAO: "#98a2b3",
    config.TT_DANG_LAM: "#1e9bf0",
    config.TT_CHO_DUYET: "#e6a700",
    config.TT_HOAN_THANH: "#12b76a",
    config.TT_LAM_LAI: "#9b8afb",
}


def status_donut(counts: dict[str, int]):
    """Biểu đồ tròn tỉ lệ việc theo trạng thái. `counts` lấy từ services.status_counts."""
    import altair as alt
    import pandas as pd

    df = pd.DataFrame({"Trạng thái": list(counts), "Số việc": list(counts.values())})
    df = df[df["Số việc"] > 0]
    mau = alt.Scale(domain=list(MAU_TRANG_THAI), range=list(MAU_TRANG_THAI.values()))
    return (alt.Chart(df)
            .mark_arc(innerRadius=55, outerRadius=105, stroke="#fff", strokeWidth=2)
            .encode(theta=alt.Theta("Số việc:Q", stack=True),
                    color=alt.Color("Trạng thái:N", scale=mau, legend=alt.Legend(title=None, orient="right")),
                    tooltip=["Trạng thái", "Số việc"])
            .properties(height=260)
            .configure(background=NEN_KHOI))


def workload_bars(bang):
    """Biểu đồ thanh ngang: số việc của từng nhân viên theo bốn nhóm. `bang` lấy từ services.workload_table."""
    import altair as alt

    dai = bang.melt(id_vars=[config.COL_ID_NV, config.COL_TEN], value_vars=config.NHOM_VIEC,
                    var_name="nhom", value_name="Số việc")
    dai["Nhóm"] = dai["nhom"].map(config.NHOM_NHAN)
    dai["Nhân viên"] = dai[config.COL_TEN]
    nhan = [config.NHOM_NHAN[n] for n in config.NHOM_VIEC]
    mau = alt.Scale(domain=nhan, range=[MAU_NHOM[n][0] for n in config.NHOM_VIEC])
    return (alt.Chart(dai)
            .mark_bar(cornerRadiusEnd=3)
            .encode(y=alt.Y("Nhân viên:N", sort=list(bang[config.COL_TEN]), title=None),
                    x=alt.X("Số việc:Q", stack="zero", axis=alt.Axis(tickMinStep=1), title="Số việc"),
                    color=alt.Color("Nhóm:N", scale=mau, legend=alt.Legend(title=None, orient="bottom", columns=2, labelLimit=200)),
                    order=alt.Order("thu_tu:Q"),
                    tooltip=["Nhân viên", "Nhóm", "Số việc"])
            .transform_calculate(thu_tu=f"indexof({nhan!r}, datum['Nhóm'])")
            .properties(height=alt.Step(32))        # mỗi nhân viên một hàng cao đều, không chồng lên nhau
            .configure(background=NEN_KHOI))
