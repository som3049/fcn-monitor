import sqlite3
from datetime import date, datetime
import streamlit as st
import pandas as pd

DB = "fcn_monitor.db"

st.set_page_config(page_title="FCN Monitor", page_icon="📊", layout="wide")

def db():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS fcn (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client TEXT NOT NULL,
        symbol TEXT NOT NULL,
        principal REAL DEFAULT 0,
        strike REAL DEFAULT 0,
        ki REAL DEFAULT 0,
        ko REAL DEFAULT 0,
        coupon REAL DEFAULT 0,
        trade_date TEXT,
        maturity_date TEXT,
        next_obs TEXT,
        final_obs TEXT,
        current_price REAL DEFAULT 0,
        status TEXT DEFAULT '持有中',
        exit_type TEXT DEFAULT '',
        notes TEXT DEFAULT ''
    )""")
    c.commit(); c.close()

def rows():
    c=db()
    x=c.execute("SELECT * FROM fcn ORDER BY id DESC").fetchall()
    c.close()
    return [dict(r) for r in x]

def add_fcn(v):
    c=db()
    c.execute("""INSERT INTO fcn
    (client,symbol,principal,strike,ki,ko,coupon,trade_date,maturity_date,next_obs,final_obs,current_price,status,exit_type,notes)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", v)
    c.commit(); c.close()

def delete_fcn(fid):
    c=db(); c.execute("DELETE FROM fcn WHERE id=?", (fid,)); c.commit(); c.close()

init_db()
st.title("📊 FCN Monitor")
st.caption("客戶 × 多筆 FCN｜第一版資料管理系統")

data = rows()

# summary
df = pd.DataFrame(data)
if len(df):
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("客戶數", df["client"].nunique())
    c2.metric("FCN 筆數", len(df))
    c3.metric("持有中", int((df["status"]=="持有中").sum()))
    c4.metric("已出場", int((df["status"]!="持有中").sum()))
else:
    st.info("目前還沒有 FCN，請從左側「新增 FCN」開始。")

with st.sidebar:
    st.header("新增 FCN")
    with st.form("add"):
        client=st.text_input("客戶名稱 *")
        symbol=st.text_input("標的 *", placeholder="例如 QCOM")
        principal=st.number_input("本金", min_value=0.0, step=1000.0)
        strike=st.number_input("Strike", min_value=0.0, step=0.01)
        ki=st.number_input("KI", min_value=0.0, step=0.01)
        ko=st.number_input("KO", min_value=0.0, step=0.01)
        coupon=st.number_input("年化票息 %", min_value=0.0, step=0.01)
        trade=st.date_input("交易日", value=date.today())
        maturity=st.date_input("到期日", value=date.today())
        next_obs=st.date_input("下一比較日", value=date.today())
        final_obs=st.date_input("最終比較日", value=date.today())
        price=st.number_input("目前價格", min_value=0.0, step=0.01)
        status=st.selectbox("狀態", ["持有中","KO 出場","到期現金贖回","到期接股","其他"])
        notes=st.text_area("備註")
        submitted=st.form_submit_button("＋ 新增")
        if submitted:
            if not client or not symbol:
                st.error("請填寫客戶名稱與標的")
            else:
                add_fcn((client,symbol.upper(),principal,strike,ki,ko,coupon,str(trade),str(maturity),
                         str(next_obs),str(final_obs),price,status,
                         "" if status=="持有中" else status,notes))
                st.success("已新增")
                st.rerun()

st.subheader("FCN 清單")
if not data:
    st.write("新增後會在這裡顯示。")
else:
    clients=["全部"]+sorted(df["client"].unique().tolist())
    pick=st.selectbox("客戶篩選", clients)
    view=df if pick=="全部" else df[df.client==pick]
    search=st.text_input("搜尋標的", placeholder="例如 QCOM / NVDA")
    if search:
        view=view[view.symbol.str.contains(search.upper(), na=False)]

    for _, r in view.iterrows():
        current=float(r.current_price or 0)
        ki=float(r.ki or 0)
        strike=float(r.strike or 0)
        ko=float(r.ko or 0)
        ki_dist=((current/ki)-1)*100 if current and ki else None
        strike_dist=((current/strike)-1)*100 if current and strike else None
        ko_dist=((ko/current)-1)*100 if current and ko else None
        try:
            days=(date.fromisoformat(r.maturity_date)-date.today()).days
        except:
            days=None

        if r.status!="持有中":
            risk="已出場"
        elif ki_dist is not None and ki_dist <= 5:
            risk="🔴 高風險"
        elif ki_dist is not None and ki_dist <= 15:
            risk="🟠 注意"
        else:
            risk="🟢 正常"

        with st.container(border=True):
            a,b,c,d,e=st.columns([2,1.2,1.2,1.2,1])
            a.markdown(f"### {r.client}｜{r.symbol}")
            b.metric("現價", f"{current:.2f}")
            c.metric("距 KI", f"{ki_dist:.1f}%" if ki_dist is not None else "-")
            d.metric("距 KO", f"{ko_dist:.1f}%" if ko_dist is not None else "-")
            e.metric("距到期", f"{days} 天" if days is not None else "-")
            st.write(f"**狀態：** {risk}　｜　產品狀態：{r.status}")
            st.caption(f"本金 {r.principal:,.0f}｜Strike {strike:.2f}｜KI {ki:.2f}｜KO {ko:.2f}｜年化票息 {r.coupon:.2f}%")
            st.caption(f"交易日 {r.trade_date}｜到期日 {r.maturity_date}｜下一比較日 {r.next_obs}｜最終比較日 {r.final_obs}")
            if r.notes:
                st.caption("備註："+r.notes)
            if st.button("刪除這筆", key=f"del_{int(r.id)}"):
                delete_fcn(int(r.id)); st.rerun()

st.divider()
st.caption("提醒：KI/KO 與最終結算的實際認定，必須依各產品正式條款；本系統目前是資料管理與監控原型。")
