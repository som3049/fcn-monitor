import streamlit as st
import sqlite3, json
from pathlib import Path
from datetime import date, datetime

st.set_page_config(page_title="FCN Monitor 3.2", page_icon="📊", layout="wide")
DB = Path("data/fcn_monitor.db")
DB.parent.mkdir(parents=True, exist_ok=True)

def get_db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = get_db()
    c.execute("""CREATE TABLE IF NOT EXISTS fcn (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_code TEXT,
        client_name TEXT NOT NULL,
        principal REAL DEFAULT 0,
        coupon REAL DEFAULT 0,
        trade_date TEXT,
        maturity_date TEXT,
        first_obs_date TEXT,
        final_obs_date TEXT,
        underlyings TEXT DEFAULT '[]',
        status TEXT DEFAULT '持有中',
        settlement TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT
    )""")
    c.commit()
    c.close()

def load_rows():
    c = get_db()
    rows = c.execute("SELECT * FROM fcn ORDER BY maturity_date, id").fetchall()
    c.close()
    return rows

def parse_us(raw):
    try:
        x = json.loads(raw or "[]")
        return x if isinstance(x, list) else []
    except Exception:
        return []

def risk_level(u):
    cur = float(u.get("current") or 0)
    ki = float(u.get("ki") or 0)
    ko = float(u.get("ko") or 0)
    if cur <= 0:
        return 0, "⚪ 未填現價"
    if ko > 0 and cur >= ko:
        return 1, "🟢 KO達標"
    if ki > 0 and cur <= ki:
        return 3, "🔴 KI以下"
    if ki > 0 and cur <= ki * 1.10:
        return 2, "🟠 接近KI"
    return 0, "🟢 正常"

def worst_of(items):
    valid = [u for u in items if float(u.get("current") or 0) > 0 and float(u.get("ki") or 0) > 0]
    return min(valid, key=lambda u: float(u["current"]) / float(u["ki"])) if valid else None

def days_left(s):
    try:
        return (date.fromisoformat(s) - date.today()).days
    except Exception:
        return None

init_db()
st.title("📊 FCN Monitor 3.2")
st.caption("客戶 × 商品代號 × 最多三檔連結標的｜WORST-OF 監控")

page = st.sidebar.radio("功能", ["總覽", "新增 FCN", "編輯 FCN", "客戶 / 商品"])
query = st.sidebar.text_input("搜尋客戶 / 商品代號 / 標的", "")

rows = load_rows()
if query:
    q = query.lower()
    rows = [r for r in rows if q in (
        (r["client_name"] or "") + " " + (r["product_code"] or "") + " " +
        " ".join(u.get("symbol","") for u in parse_us(r["underlyings"]))
    ).lower()]

if page == "總覽":
    client_count = len(set(r["client_name"] for r in rows))
    near = high = expiring = 0
    for r in rows:
        items = parse_us(r["underlyings"])
        levels = [risk_level(u)[0] for u in items]
        level = max(levels or [0])
        near += level == 2
        high += level == 3
        d = days_left(r["maturity_date"])
        expiring += d is not None and 0 <= d <= 7

    a,b,c,d,e = st.columns(5)
    a.metric("客戶", client_count)
    b.metric("FCN", len(rows))
    c.metric("正常", max(0, len(rows)-near-high))
    d.metric("接近 / 高風險", f"{near} / {high}")
    e.metric("7天內到期", expiring)
    st.divider()

    if not rows:
        st.info("目前沒有 FCN，請從「新增 FCN」開始。")

    for r in rows:
        items = parse_us(r["underlyings"])
        levels = [risk_level(u)[0] for u in items]
        level = max(levels or [0])
        badge = "🔴" if level == 3 else "🟠" if level == 2 else "🟢"
        w = worst_of(items)
        d = days_left(r["maturity_date"])
        st.markdown(f"### {badge} {r['client_name']} ｜ `{r['product_code'] or '-'}`")
        x,y,z,t = st.columns(4)
        x.write(f"**本金**\n{r['principal']:,.0f}")
        y.write(f"**年化票息**\n{r['coupon']:.2f}%")
        z.write(f"**到期**\n{r['maturity_date'] or '-'}\n剩 {d if d is not None else '-'} 天")
        t.write(f"**WORST-OF**\n{w.get('symbol') if w else '-'}")
        if w:
            ratio = float(w["current"]) / float(w["ki"]) * 100 if float(w["ki"]) else 0
            st.caption(f"WORST-OF {w['symbol']}｜KI位置 {ratio:.2f}%")
        st.caption(" ｜ ".join(
            f"{u.get('symbol','-')}: 現價 {u.get('current') or '-'} / Strike {u.get('strike') or '-'} / KI {u.get('ki') or '-'} / KO {u.get('ko') or '-'}"
            for u in items
        ))
        st.divider()

elif page == "新增 FCN":
    st.subheader("➕ 新增 FCN")
    with st.form("new_fcn"):
        a,b = st.columns(2)
        client = a.text_input("客戶名稱 *")
        code = b.text_input("商品代號 *", placeholder="例如 FCN202609001")

        a,b,c = st.columns(3)
        principal = a.number_input("本金", min_value=0.0, step=1000.0)
        coupon = b.number_input("年化票息 (%)", min_value=0.0, step=0.01)
        status = c.selectbox("狀態", ["持有中","KO 出場","到期現金贖回","到期接股","其他"])

        a,b,c,d = st.columns(4)
        td = a.date_input("交易日", date.today())
        md = b.date_input("到期日", date.today())
        fo = c.date_input("首次比價日", date.today())
        final = d.date_input("最後觀察日", date.today())

        settlement = st.text_input("結算方式", placeholder="現金贖回 / 實物交割 / 依條款")
        notes = st.text_area("備註 / 條款提醒")

        items = []
        st.markdown("### 🔗 連結標的（最多 3 檔）")
        for i in range(3):
            st.markdown(f"**標的 {i+1}**")
            a,b,c,d,e = st.columns(5)
            sym = a.text_input("代號", key=f"n_sym_{i}")
            initial = b.number_input("期初價", min_value=0.0, step=0.01, key=f"n_initial_{i}")
            strike = c.number_input("Strike", min_value=0.0, step=0.01, key=f"n_strike_{i}")
            ki = d.number_input("KI", min_value=0.0, step=0.01, key=f"n_ki_{i}")
            ko = e.number_input("KO", min_value=0.0, step=0.01, key=f"n_ko_{i}")
            current = st.number_input("目前價格", min_value=0.0, step=0.01, key=f"n_current_{i}")
            if sym.strip():
                items.append({"symbol":sym.strip().upper(),"initial":initial,"strike":strike,"ki":ki,"ko":ko,"current":current})

        submitted = st.form_submit_button("💾 儲存 FCN", type="primary")

    if submitted:
        if not client.strip() or not code.strip():
            st.error("客戶名稱與商品代號必填。")
        else:
            c = get_db()
            c.execute("""INSERT INTO fcn
                (product_code,client_name,principal,coupon,trade_date,maturity_date,
                 first_obs_date,final_obs_date,underlyings,status,settlement,notes,created_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (code.strip(), client.strip(), principal, coupon, str(td), str(md), str(fo), str(final),
                 json.dumps(items, ensure_ascii=False), status, settlement, notes,
                 datetime.now().isoformat(timespec="seconds")))
            c.commit(); c.close()
            st.success("FCN 已新增。")
            st.rerun()

elif page == "編輯 FCN":
    st.subheader("✏️ 編輯 FCN")
    if not rows:
        st.info("沒有符合條件的 FCN。")
    else:
        mapping = {f"{r['client_name']}｜{r['product_code'] or '-'}｜#{r['id']}":r for r in rows}
        selected = st.selectbox("選擇商品", list(mapping))
        r = mapping[selected]
        old = parse_us(r["underlyings"]) + [{}] * 3

        def parse_date(s):
            try: return date.fromisoformat(s)
            except Exception: return date.today()

        with st.form("edit_fcn"):
            a,b = st.columns(2)
            client = a.text_input("客戶名稱 *", r["client_name"])
            code = b.text_input("商品代號 *", r["product_code"] or "")
            a,b,c = st.columns(3)
            principal = a.number_input("本金", min_value=0.0, value=float(r["principal"] or 0), step=1000.0)
            coupon = b.number_input("年化票息 (%)", min_value=0.0, value=float(r["coupon"] or 0), step=0.01)
            choices = ["持有中","KO 出場","到期現金贖回","到期接股","其他"]
            status = c.selectbox("狀態", choices, index=choices.index(r["status"]) if r["status"] in choices else 0)
            a,b,c,d = st.columns(4)
            td = a.date_input("交易日", parse_date(r["trade_date"]))
            md = b.date_input("到期日", parse_date(r["maturity_date"]))
            fo = c.date_input("首次比價日", parse_date(r["first_obs_date"]))
            final = d.date_input("最後觀察日", parse_date(r["final_obs_date"]))
            settlement = st.text_input("結算方式", r["settlement"] or "")
            notes = st.text_area("備註 / 條款提醒", r["notes"] or "")

            items = []
            st.markdown("### 🔗 連結標的（最多 3 檔）")
            for i in range(3):
                u = old[i]
                a,b,c,d,e = st.columns(5)
                sym = a.text_input("代號", u.get("symbol",""), key=f"e_sym_{i}")
                initial = b.number_input("期初價", min_value=0.0, value=float(u.get("initial") or 0), step=0.01, key=f"e_initial_{i}")
                strike = c.number_input("Strike", min_value=0.0, value=float(u.get("strike") or 0), step=0.01, key=f"e_strike_{i}")
                ki = d.number_input("KI", min_value=0.0, value=float(u.get("ki") or 0), step=0.01, key=f"e_ki_{i}")
                ko = e.number_input("KO", min_value=0.0, value=float(u.get("ko") or 0), step=0.01, key=f"e_ko_{i}")
                current = st.number_input("目前價格", min_value=0.0, value=float(u.get("current") or 0), step=0.01, key=f"e_current_{i}")
                if sym.strip():
                    items.append({"symbol":sym.strip().upper(),"initial":initial,"strike":strike,"ki":ki,"ko":ko,"current":current})

            submitted = st.form_submit_button("💾 儲存修改", type="primary")

        if submitted:
            c = get_db()
            c.execute("""UPDATE fcn SET product_code=?,client_name=?,principal=?,coupon=?,
                trade_date=?,maturity_date=?,first_obs_date=?,final_obs_date=?,
                underlyings=?,status=?,settlement=?,notes=? WHERE id=?""",
                (code.strip(), client.strip(), principal, coupon, str(td), str(md), str(fo), str(final),
                 json.dumps(items, ensure_ascii=False), status, settlement, notes, r["id"]))
            c.commit(); c.close()
            st.success("已更新。")
            st.rerun()

        if st.button("🗑️ 刪除這筆 FCN"):
            c = get_db(); c.execute("DELETE FROM fcn WHERE id=?", (r["id"],)); c.commit(); c.close()
            st.success("已刪除。"); st.rerun()

else:
    st.subheader("👤 客戶 / 商品")
    groups = {}
    for r in rows:
        groups.setdefault(r["client_name"], []).append(r)
    if not groups:
        st.info("尚無資料。")
    for client, rs in groups.items():
        with st.expander(f"👤 {client}｜{len(rs)} 筆 FCN", expanded=True):
            for r in rs:
                items = parse_us(r["underlyings"])
                w = worst_of(items)
                d = days_left(r["maturity_date"])
                st.markdown(f"**{r['product_code'] or '-'}**｜到期 {r['maturity_date'] or '-'}｜剩 {d if d is not None else '-'} 天")
                st.write(f"本金 {r['principal']:,.0f}｜票息 {r['coupon']:.2f}%｜狀態 {r['status']}｜WORST-OF {(w or {}).get('symbol','-')}")
                st.caption("、".join(u.get("symbol","-") for u in items) or "尚未設定標的")

st.sidebar.divider()
st.sidebar.caption("FCN Monitor 3.2\n最多三檔連結標的｜WORST-OF")
