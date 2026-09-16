import streamlit as st
import sqlite3, json, urllib.request, urllib.parse
from pathlib import Path
from datetime import date, datetime

st.set_page_config(page_title="FCN Monitor 3.3", page_icon="📊", layout="wide")
DB = Path("data/fcn_monitor.db")
DB.parent.mkdir(parents=True, exist_ok=True)

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS fcn(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      product_code TEXT, client_name TEXT NOT NULL,
      principal REAL DEFAULT 0, coupon REAL DEFAULT 0,
      trade_date TEXT, maturity_date TEXT, first_obs_date TEXT,
      final_obs_date TEXT, underlyings TEXT DEFAULT '[]',
      status TEXT DEFAULT '持有中', settlement TEXT DEFAULT '',
      notes TEXT DEFAULT '', created_at TEXT)""")
    c.commit(); c.close()

def rows():
    c = db()
    r = c.execute("SELECT * FROM fcn ORDER BY maturity_date,id").fetchall()
    c.close()
    return r

def parse(x):
    try:
        y = json.loads(x or "[]")
        return y if isinstance(y,list) else []
    except Exception:
        return []

@st.cache_data(ttl=60)
def live_price(symbol):
    try:
        url = ("https://query1.finance.yahoo.com/v8/finance/chart/" +
               urllib.parse.quote(symbol.upper()) +
               "?range=1d&interval=1m")
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
        meta = data["chart"]["result"][0].get("meta", {})
        p = meta.get("regularMarketPrice")
        if p is None:
            q = data["chart"]["result"][0]["indicators"]["quote"][0]
            vals = [v for v in q.get("close",[]) if v is not None]
            p = vals[-1] if vals else None
        return float(p) if p is not None else None
    except Exception:
        return None

def risk(u):
    p=float(u.get("current") or 0); ki=float(u.get("ki") or 0); ko=float(u.get("ko") or 0)
    if p<=0: return 0,"⚪ 無行情"
    if ko>0 and p>=ko: return 1,"🟢 KO達標"
    if ki>0 and p<=ki: return 3,"🔴 KI以下"
    if ki>0 and p<=ki*1.10: return 2,"🟠 接近KI"
    return 0,"🟢 正常"

def live_items(r):
    result=[]
    for u in parse(r["underlyings"]):
        x=dict(u)
        p=live_price(x.get("symbol","")) if x.get("symbol") else None
        x["current"] = p if p is not None else float(x.get("current") or 0)
        result.append(x)
    return result

def worst(items):
    v=[u for u in items if float(u.get("current") or 0)>0 and float(u.get("ki") or 0)>0]
    return min(v,key=lambda u:float(u["current"])/float(u["ki"])) if v else None

def days(s):
    try:return (date.fromisoformat(s)-date.today()).days
    except:return None

init_db()
st.title("📊 FCN Monitor 3.3")
st.caption("自動行情版｜客戶 × 商品代號 × 最多三檔標的 × WORST-OF")

st.sidebar.subheader("行情")
ttl=st.sidebar.slider("行情快取（秒）",15,300,60,15)
if st.sidebar.button("🔄 立即更新"):
    live_price.clear()
    st.rerun()
st.sidebar.caption(f"行情來源：Yahoo Finance 公開行情介面\\n快取：{ttl} 秒")

page=st.sidebar.radio("功能",["總覽","新增 FCN","編輯 FCN","客戶 / 商品"])
q=st.sidebar.text_input("搜尋客戶 / 商品代號 / 標的")
data=rows()
if q:
    q=q.lower()
    data=[r for r in data if q in ((r["client_name"] or "")+" "+(r["product_code"] or "")+" "+" ".join(u.get("symbol","") for u in parse(r["underlyings"]))).lower()]

if page=="總覽":
    live=[(r,live_items(r)) for r in data]
    levels=[max([risk(u)[0] for u in us] or [0]) for _,us in live]
    near=sum(x==2 for x in levels); high=sum(x==3 for x in levels)
    exp=sum(0<=days(r["maturity_date"])<=7 for r,_ in live if days(r["maturity_date"]) is not None)
    a,b,c,d,e=st.columns(5)
    a.metric("客戶",len(set(r["client_name"] for r,_ in live)))
    b.metric("FCN",len(live)); c.metric("正常",max(0,len(live)-near-high))
    d.metric("接近 / 高風險",f"{near} / {high}"); e.metric("7天內到期",exp)
    st.divider()
    for r,us in live:
        level=max([risk(u)[0] for u in us] or [0])
        badge="🔴" if level==3 else "🟠" if level==2 else "🟢"
        w=worst(us); dl=days(r["maturity_date"])
        st.markdown(f"### {badge} {r['client_name']}｜`{r['product_code'] or '-'}`")
        a,b,c,d=st.columns(4)
        a.write(f"**本金**\\n{r['principal']:,.0f}")
        b.write(f"**票息**\\n{r['coupon']:.2f}%")
        c.write(f"**到期**\\n{r['maturity_date'] or '-'}\\n剩 {dl if dl is not None else '-'} 天")
        d.write(f"**WORST-OF**\\n{w.get('symbol') if w else '-'}")
        for u in us:
            p=float(u.get("current") or 0); ki=float(u.get("ki") or 0); strike=float(u.get("strike") or 0); ko=float(u.get("ko") or 0)
            pos=p/ki*100 if p and ki else 0
            st.write(f"**{u.get('symbol','-')}**　現價 **{p:g}**　｜Strike {strike:g}｜KI {ki:g}｜KO {ko:g}｜KI位置 **{pos:.2f}%**　｜{risk(u)[1]}")
        st.divider()

elif page=="新增 FCN":
    st.subheader("➕ 新增 FCN")
    with st.form("new"):
        a,b=st.columns(2); client=a.text_input("客戶名稱 *"); code=b.text_input("商品代號 *")
        a,b,c=st.columns(3); principal=a.number_input("本金",min_value=0.,step=1000.); coupon=b.number_input("年化票息 (%)",min_value=0.,step=.01); status=c.selectbox("狀態",["持有中","KO 出場","到期現金贖回","到期接股","其他"])
        a,b,c,d=st.columns(4); td=a.date_input("交易日",date.today()); md=b.date_input("到期日",date.today()); fo=c.date_input("首次比價日",date.today()); final=d.date_input("最後觀察日",date.today())
        settlement=st.text_input("結算方式"); notes=st.text_area("備註 / 條款提醒")
        us=[]
        for i in range(3):
            st.markdown(f"**連結標的 {i+1}**")
            a,b,c,d,e=st.columns(5)
            sym=a.text_input("代號",key=f"ns{i}"); ini=b.number_input("期初價",min_value=0.,step=.01,key=f"ni{i}"); strike=c.number_input("Strike",min_value=0.,step=.01,key=f"nk{i}"); ki=d.number_input("KI",min_value=0.,step=.01,key=f"nki{i}"); ko=e.number_input("KO",min_value=0.,step=.01,key=f"nko{i}")
            if sym.strip(): us.append({"symbol":sym.strip().upper(),"initial":ini,"strike":strike,"ki":ki,"ko":ko,"current":0})
        ok=st.form_submit_button("💾 儲存 FCN",type="primary")
    if ok:
        if not client.strip() or not code.strip(): st.error("客戶名稱與商品代號必填。")
        else:
            c=db()
            c.execute("""INSERT INTO fcn(product_code,client_name,principal,coupon,trade_date,maturity_date,first_obs_date,final_obs_date,underlyings,status,settlement,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",(code.strip(),client.strip(),principal,coupon,str(td),str(md),str(fo),str(final),json.dumps(us),status,settlement,notes,datetime.now().isoformat()))
            c.commit(); c.close(); st.success("已新增"); st.rerun()

elif page=="編輯 FCN":
    st.subheader("✏️ 編輯 FCN")
    if not data: st.info("沒有資料")
    else:
        mp={f"{r['client_name']}｜{r['product_code'] or '-'}｜#{r['id']}":r for r in data}
        r=mp[st.selectbox("選擇商品",list(mp))]
        old=parse(r["underlyings"])+[{}]*3
        def D(x):
            try:return date.fromisoformat(x)
            except:return date.today()
        with st.form("edit"):
            a,b=st.columns(2); client=a.text_input("客戶名稱",r["client_name"]); code=b.text_input("商品代號",r["product_code"] or "")
            a,b,c=st.columns(3); principal=a.number_input("本金",min_value=0.,value=float(r["principal"] or 0),step=1000.); coupon=b.number_input("年化票息 (%)",min_value=0.,value=float(r["coupon"] or 0),step=.01); choices=["持有中","KO 出場","到期現金贖回","到期接股","其他"]; status=c.selectbox("狀態",choices,index=choices.index(r["status"]) if r["status"] in choices else 0)
            a,b,c,d=st.columns(4); td=a.date_input("交易日",D(r["trade_date"])); md=b.date_input("到期日",D(r["maturity_date"])); fo=c.date_input("首次比價日",D(r["first_obs_date"])); final=d.date_input("最後觀察日",D(r["final_obs_date"]))
            settlement=st.text_input("結算方式",r["settlement"] or ""); notes=st.text_area("備註",r["notes"] or "")
            us=[]
            for i in range(3):
                u=old[i]; a,b,c,d,e=st.columns(5)
                sym=a.text_input("代號",u.get("symbol",""),key=f"es{i}"); ini=b.number_input("期初價",min_value=0.,value=float(u.get("initial") or 0),step=.01,key=f"ei{i}"); strike=c.number_input("Strike",min_value=0.,value=float(u.get("strike") or 0),step=.01,key=f"ek{i}"); ki=d.number_input("KI",min_value=0.,value=float(u.get("ki") or 0),step=.01,key=f"eki{i}"); ko=e.number_input("KO",min_value=0.,value=float(u.get("ko") or 0),step=.01,key=f"eko{i}")
                if sym.strip():us.append({"symbol":sym.strip().upper(),"initial":ini,"strike":strike,"ki":ki,"ko":ko,"current":float(u.get("current") or 0)})
            ok=st.form_submit_button("💾 儲存修改",type="primary")
        if ok:
            c=db()
            c.execute("""UPDATE fcn SET product_code=?,client_name=?,principal=?,coupon=?,trade_date=?,maturity_date=?,first_obs_date=?,final_obs_date=?,underlyings=?,status=?,settlement=?,notes=? WHERE id=?""",(code.strip(),client.strip(),principal,coupon,str(td),str(md),str(fo),str(final),json.dumps(us),status,settlement,notes,r["id"]))
            c.commit(); c.close(); st.success("已更新"); st.rerun()
        if st.button("🗑️ 刪除這筆 FCN"):
            c=db(); c.execute("DELETE FROM fcn WHERE id=?",(r["id"],)); c.commit(); c.close(); st.rerun()

else:
    st.subheader("👤 客戶 / 商品")
    groups={}
    for r in data: groups.setdefault(r["client_name"],[]).append(r)
    for client,rs in groups.items():
        with st.expander(f"👤 {client}｜{len(rs)} 筆",True):
            for r in rs:
                us=live_items(r); w=worst(us)
                st.markdown(f"**{r['product_code'] or '-'}**｜到期 {r['maturity_date'] or '-'}｜剩 {days(r['maturity_date']) if days(r['maturity_date']) is not None else '-'} 天")
                st.write(f"本金 {r['principal']:,.0f}｜票息 {r['coupon']:.2f}%｜狀態 {r['status']}｜WORST-OF {(w or {}).get('symbol','-')}")
                st.caption("、".join(f"{u.get('symbol','-')} {float(u.get('current') or 0):g}" for u in us))
