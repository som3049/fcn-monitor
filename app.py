import sqlite3
from datetime import date, datetime
import streamlit as st
import pandas as pd

DB="fcn_monitor.db"
st.set_page_config(page_title="FCN Monitor 3.0", page_icon="📊", layout="wide")

def conn():
    c=sqlite3.connect(DB, check_same_thread=False)
    c.row_factory=sqlite3.Row
    return c

def init():
    c=conn()
    c.execute("""CREATE TABLE IF NOT EXISTS fcn(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      client TEXT NOT NULL, symbol TEXT NOT NULL, principal REAL DEFAULT 0,
      strike REAL DEFAULT 0, ki REAL DEFAULT 0, ko REAL DEFAULT 0,
      coupon REAL DEFAULT 0, trade_date TEXT, maturity_date TEXT,
      next_obs TEXT, final_obs TEXT, current_price REAL DEFAULT 0,
      status TEXT DEFAULT '持有中', exit_type TEXT DEFAULT '',
      ki_touched INTEGER DEFAULT 0, notes TEXT DEFAULT ''
    )""")
    c.commit(); c.close()

def all_rows():
    c=conn(); rows=[dict(x) for x in c.execute("SELECT * FROM fcn ORDER BY id DESC")]; c.close()
    return rows

def add(v):
    c=conn(); c.execute("""INSERT INTO fcn
    (client,symbol,principal,strike,ki,ko,coupon,trade_date,maturity_date,next_obs,final_obs,current_price,status,exit_type,ki_touched,notes)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",v); c.commit(); c.close()

def update(fid,v):
    c=conn(); c.execute("""UPDATE fcn SET
    client=?,symbol=?,principal=?,strike=?,ki=?,ko=?,coupon=?,trade_date=?,maturity_date=?,next_obs=?,final_obs=?,current_price=?,status=?,exit_type=?,ki_touched=?,notes=?
    WHERE id=?""",(*v,fid)); c.commit(); c.close()

def delete(fid):
    c=conn(); c.execute("DELETE FROM fcn WHERE id=?",(fid,)); c.commit(); c.close()

def risk(row):
    if row["status"]!="持有中": return "已出場"
    p=float(row["current_price"] or 0); ki=float(row["ki"] or 0)
    if not p or not ki: return "⚪ 未設定價格"
    d=(p/ki-1)*100
    return "🔴 高風險" if d<=5 else ("🟠 注意" if d<=15 else "🟢 正常")

def dist(p,t):
    return (p/t-1)*100 if p and t else None

init()
st.markdown("## 📊 FCN Monitor 3.0")
st.caption("客戶 × 多筆 FCN｜持有／KO／接股｜KI・Strike・KO 監控")

rows=all_rows()
df=pd.DataFrame(rows)

if len(df):
    today=date.today()
    days=[]
    for x in df["maturity_date"]:
        try: days.append((date.fromisoformat(x)-today).days)
        except: days.append(None)
    df["days_to_maturity"]=days
    df["risk"]=df.apply(risk,axis=1)
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("客戶",df.client.nunique())
    c2.metric("FCN",len(df))
    c3.metric("持有中",int((df.status=="持有中").sum()))
    c4.metric("高風險",int((df.risk=="🔴 高風險").sum()))
    c5.metric("7天內到期",int(((df.days_to_maturity>=0)&(df.days_to_maturity<=7)).sum()))
else:
    st.info("尚無資料。請在「＋ 新增 FCN」建立第一筆。")

tab1,tab2,tab3=st.tabs(["📋 FCN 總覽","👤 客戶視角","＋ 新增 FCN"])

with tab1:
    if len(df):
        a,b,c=st.columns([1.3,1,1])
        client_filter=a.selectbox("客戶",["全部"]+sorted(df.client.unique()))
        status_filter=b.selectbox("產品狀態",["全部","持有中","KO 出場","到期現金贖回","到期接股","其他"])
        q=c.text_input("搜尋標的",placeholder="QCOM / NVDA")
        v=df.copy()
        if client_filter!="全部": v=v[v.client==client_filter]
        if status_filter!="全部": v=v[v.status==status_filter]
        if q: v=v[v.symbol.str.contains(q.upper(),na=False)]
        st.caption(f"顯示 {len(v)} 筆")
        for _,r in v.iterrows():
            p=float(r.current_price or 0)
            kd=dist(p,float(r.ki or 0)); sd=dist(p,float(r.strike or 0)); cod=dist(p,float(r.ko or 0))
            with st.container(border=True):
                h1,h2,h3,h4,h5=st.columns([2.2,1,1,1,1])
                h1.markdown(f"### {r.client} · {r.symbol}")
                h2.metric("現價",f"{p:.2f}")
                h3.metric("距 KI",f"{kd:.1f}%" if kd is not None else "-")
                h4.metric("距 Strike",f"{sd:.1f}%" if sd is not None else "-")
                h5.metric("距 KO",f"{cod:.1f}%" if cod is not None else "-")
                st.write(f"**{r.risk}**　｜　{r.status}　｜　到期：{r.maturity_date}　｜　剩餘：{r.days_to_maturity} 天")
                st.caption(f"本金 {r.principal:,.0f}｜Strike {r.strike:.2f}｜KI {r.ki:.2f}｜KO {r.ko:.2f}｜年化票息 {r.coupon:.2f}%")
                st.caption(f"下一比較日 {r.next_obs}｜最終比較日 {r.final_obs}｜KI曾觸及：{'是' if r.ki_touched else '否'}")
                if r.notes: st.caption("備註："+r.notes)
                e1,e2=st.columns(2)
                if e1.button("編輯",key=f"edit{int(r.id)}"):
                    st.session_state["edit_id"]=int(r.id)
                if e2.button("刪除",key=f"del{int(r.id)}"):
                    delete(int(r.id)); st.rerun()

with tab2:
    if len(df):
        client=st.selectbox("選擇客戶",sorted(df.client.unique()),key="client_view")
        v=df[df.client==client]
        st.markdown(f"### {client} 的 FCN")
        st.write(f"共 **{len(v)} 筆**，持有中 **{int((v.status=='持有中').sum())} 筆**")
        show=v[["symbol","principal","current_price","strike","ki","ko","coupon","maturity_date","status","risk"]].copy()
        show.columns=["標的","本金","現價","Strike","KI","KO","年化票息%","到期日","狀態","風險"]
        st.dataframe(show,use_container_width=True,hide_index=True)
    else: st.info("尚無客戶資料。")

with tab3:
    edit_id=st.session_state.get("edit_id")
    existing=next((x for x in rows if x["id"]==edit_id),None)
    title="編輯 FCN" if existing else "新增 FCN"
    st.subheader(title)
    with st.form("fcn_form"):
        c1,c2=st.columns(2)
        client=c1.text_input("客戶名稱 *",value=existing["client"] if existing else "")
        symbol=c2.text_input("標的 *",value=existing["symbol"] if existing else "",placeholder="QCOM")
        c3,c4,c5=st.columns(3)
        principal=c3.number_input("本金",min_value=0.0,value=float(existing["principal"]) if existing else 100000.0,step=1000.0)
        strike=c4.number_input("Strike",min_value=0.0,value=float(existing["strike"]) if existing else 0.0,step=0.01)
        ki=c5.number_input("KI",min_value=0.0,value=float(existing["ki"]) if existing else 0.0,step=0.01)
        c6,c7,c8=st.columns(3)
        ko=c6.number_input("KO",min_value=0.0,value=float(existing["ko"]) if existing else 0.0,step=0.01)
        coupon=c7.number_input("年化票息 %",min_value=0.0,value=float(existing["coupon"]) if existing else 0.0,step=0.01)
        price=c8.number_input("目前價格",min_value=0.0,value=float(existing["current_price"]) if existing else 0.0,step=0.01)
        c9,c10,c11,c12=st.columns(4)
        trade=c9.date_input("交易日",value=date.fromisoformat(existing["trade_date"]) if existing and existing["trade_date"] else date.today())
        maturity=c10.date_input("到期日",value=date.fromisoformat(existing["maturity_date"]) if existing and existing["maturity_date"] else date.today())
        next_obs=c11.date_input("下一比較日",value=date.fromisoformat(existing["next_obs"]) if existing and existing["next_obs"] else date.today())
        final_obs=c12.date_input("最終比較日",value=date.fromisoformat(existing["final_obs"]) if existing and existing["final_obs"] else date.today())
        status=st.selectbox("產品狀態",["持有中","KO 出場","到期現金贖回","到期接股","其他"],index=["持有中","KO 出場","到期現金贖回","到期接股","其他"].index(existing["status"]) if existing else 0)
        ki_touched=st.checkbox("KI 曾被觸及（依產品條款確認）",value=bool(existing["ki_touched"]) if existing else False)
        notes=st.text_area("備註",value=existing["notes"] if existing else "")
        submitted=st.form_submit_button("儲存")
        if submitted:
            if not client.strip() or not symbol.strip():
                st.error("請填寫客戶名稱與標的")
            else:
                vals=(client.strip(),symbol.strip().upper(),principal,strike,ki,ko,coupon,str(trade),str(maturity),str(next_obs),str(final_obs),price,status,status if status!="持有中" else "",int(ki_touched),notes)
                if existing: update(edit_id,vals); st.session_state.pop("edit_id",None)
                else: add(vals)
                st.success("已儲存"); st.rerun()

st.divider()
st.caption("FCN Monitor 3.0｜實際 KI/KO、觀察方式與最終結算請以各產品正式條款為準。")
