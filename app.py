"""
Money Tracker — Streamlit + Supabase (falls back to local SQLite)
Run:  streamlit run app.py

Backend:
  * If .env (next to this file) has SUPABASE_URL + SUPABASE_KEY  -> Supabase
  * Otherwise                                                    -> local expenses.db
"""
import os
import sqlite3
import hmac
from datetime import date, datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).with_name(".env"))
except ImportError:
    pass

DB_PATH = Path(__file__).with_name("expenses.db")


def setting(name, default=""):
    """Read a setting from .env / environment first, then Streamlit secrets (Cloud)."""
    val = os.getenv(name)
    if not val:
        try:
            val = st.secrets.get(name, default)
        except Exception:  # no secrets.toml locally
            val = default
    return str(val or "").strip().strip('"')


SUPABASE_URL = setting("SUPABASE_URL")
SUPABASE_KEY = setting("SUPABASE_KEY")
APP_PASSWORD = setting("APP_PASSWORD")
TZ = ZoneInfo(setting("APP_TIMEZONE", "Asia/Dhaka") or "Asia/Dhaka")


def bd_today():
    """Today's date in Bangladesh time (cloud servers run on UTC)."""
    return datetime.now(TZ).date()
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)
CURRENCY = "৳"
APP_NAME = "খরচের হিসাব"   # <- app er naam bodlate shudhu eta bodlao

DEFAULT_CATEGORIES = [
    "বাজার", "খাবার / রেস্টুরেন্ট", "যাতায়াত", "বাইক / গাড়ি", "বাসা ভাড়া",
    "বিদ্যুৎ বিল", "গ্যাস বিল", "পানি বিল", "ইন্টারনেট", "মোবাইল রিচার্জ",
    "চিকিৎসা / ওষুধ", "শিক্ষা", "কাপড় / শপিং", "পরিবার", "বুয়া / কাজের লোক",
    "দাওয়াত / উপহার", "দান / সদকা", "কাজ / ব্যবসা", "বিনোদন", "অন্যান্য",
]
# old English names -> Bangla (migrates existing databases automatically)
CATEGORY_RENAME = {
    "Bazar": "বাজার", "Food / Restaurant": "খাবার / রেস্টুরেন্ট", "Transport": "যাতায়াত",
    "House rent": "বাসা ভাড়া", "Utility bills": "বিদ্যুৎ বিল", "Internet & Mobile": "ইন্টারনেট",
    "Health / Medicine": "চিকিৎসা / ওষুধ", "Education": "শিক্ষা",
    "Shopping / Clothing": "কাপড় / শপিং", "Family": "পরিবার", "Work / Business": "কাজ / ব্যবসা",
    "Entertainment": "বিনোদন", "Others": "অন্যান্য",
}
DEFAULT_PAYMENTS = ["ক্যাশ", "বিকাশ", "নগদ", "রকেট", "কার্ড", "ব্যাংক ট্রান্সফার"]
PAYMENT_RENAME = {"Cash": "ক্যাশ", "bKash": "বিকাশ", "Nagad": "নগদ", "Rocket": "রকেট",
                  "Card": "কার্ড", "Bank transfer": "ব্যাংক ট্রান্সফার"}

CAT_ICON = {
    "বাজার": "🛒", "খাবার / রেস্টুরেন্ট": "🍽️", "যাতায়াত": "🚌", "বাইক / গাড়ি": "🏍️",
    "বাসা ভাড়া": "🏠", "বিদ্যুৎ বিল": "💡", "গ্যাস বিল": "🔥", "পানি বিল": "💧",
    "ইন্টারনেট": "🌐", "মোবাইল রিচার্জ": "📱", "চিকিৎসা / ওষুধ": "💊", "শিক্ষা": "📚",
    "কাপড় / শপিং": "👕", "পরিবার": "👨‍👩‍👧", "বুয়া / কাজের লোক": "🧹",
    "দাওয়াত / উপহার": "🎁", "দান / সদকা": "🤲", "কাজ / ব্যবসা": "💼", "বিনোদন": "🎬",
    "অন্যান্য": "📦",
}

SEED_ROWS = [
    ("2026-10-02", "অন্যান্য", "Rejowan Vai", 3000, "ব্যাংক ট্রান্সফার"),
    ("2026-10-03", "খাবার / রেস্টুরেন্ট", "Nabil Restaurant", 380, "ক্যাশ"),
    ("2026-10-04", "অন্যান্য", "Bike Eng. Oil + Chain lop + Breakfast + lunch", 1460, "ক্যাশ"),
    ("2026-10-04", "অন্যান্য", "Bike oil Load", 800, "ক্যাশ"),
    ("2026-10-06", "পরিবার", "Ruku", 1000, "ব্যাংক ট্রান্সফার"),
    ("2026-10-07", "পরিবার", "Mama", 4000, "ব্যাংক ট্রান্সফার"),
    ("2026-10-08", "পরিবার", "Baba & Maa", 2550, "ব্যাংক ট্রান্সফার"),
    ("2026-10-08", "খাবার / রেস্টুরেন্ট", "Chal", 1500, "ক্যাশ"),
    ("2026-10-08", "বাজার", "Milk - 5lr", 560, "ক্যাশ"),
    ("2026-10-08", "বাজার", "Mach", 1300, "ক্যাশ"),
    ("2026-10-08", "বাজার", "Vegetable", 610, "ক্যাশ"),
    ("2026-10-08", "বাজার", "Shopno Supershop", 575, "ক্যাশ"),
    ("2026-10-08", "বাজার", "Beef", 1000, "ক্যাশ"),
]

# Theme
BG, CARD, BORDER = "#F3F6F2", "#FFFFFF", "#E5ECE6"
GREEN, GREEN_DIM, DEEP, MINT = "#059669", "#A7F3D0", "#064E3B", "#ECFDF5"
TEXT, MUTED = "#0B1F17", "#6B7C74"
RED, AMBER = "#DC2626", "#D97706"


# ---------------------------------------------------------------- database
EXP_COLS = ["id", "date", "category", "description", "amount", "payment_method", "created_at"]


# ---- local SQLite -------------------------------------------------------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_sqlite():
    with get_conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            name TEXT PRIMARY KEY, monthly_budget REAL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS payment_methods (name TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            amount REAL NOT NULL CHECK (amount > 0),
            payment_method TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS idx_exp_date ON expenses(date);
        """)
        for old, new in CATEGORY_RENAME.items():
            row = c.execute("SELECT monthly_budget FROM categories WHERE name=?", (old,)).fetchone()
            if row:
                c.execute("INSERT OR IGNORE INTO categories(name, monthly_budget) VALUES (?,?)",
                          (new, row[0]))
                c.execute("DELETE FROM categories WHERE name=?", (old,))
            c.execute("UPDATE expenses SET category=? WHERE category=?", (new, old))
        c.executemany("INSERT OR IGNORE INTO categories(name) VALUES (?)",
                      [(x,) for x in DEFAULT_CATEGORIES])
        for old, new in PAYMENT_RENAME.items():
            if c.execute("SELECT 1 FROM payment_methods WHERE name=?", (old,)).fetchone():
                c.execute("INSERT OR IGNORE INTO payment_methods(name) VALUES (?)", (new,))
                c.execute("DELETE FROM payment_methods WHERE name=?", (old,))
            c.execute("UPDATE expenses SET payment_method=? WHERE payment_method=?", (new, old))
        c.executemany("INSERT OR IGNORE INTO payment_methods(name) VALUES (?)",
                      [(x,) for x in DEFAULT_PAYMENTS])
        if c.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 0:
            c.executemany("INSERT INTO expenses(date, category, description, amount, "
                          "payment_method) VALUES (?,?,?,?,?)", SEED_ROWS)


def sql_q(sql, params=()):
    with get_conn() as c:
        return pd.read_sql_query(sql, c, params=params)


def sql_run(sql, params=()):
    with get_conn() as c:
        c.execute(sql, params)


# ---- Supabase -----------------------------------------------------------
@st.cache_resource(show_spinner=False)
def sb():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def sb_all(query_fn, page=1000):
    """Fetch every row (Supabase returns max 1000 per request)."""
    rows, start = [], 0
    while True:
        chunk = query_fn().range(start, start + page - 1).execute().data
        rows += chunk
        if len(chunk) < page:
            return rows
        start += page


def sb_seed_lookups():
    """Make sure default categories / payment methods exist (safe to run every start)."""
    t = sb()
    t.table("categories").upsert(
        [{"name": n, "sort_order": i + 1} for i, n in enumerate(DEFAULT_CATEGORIES)],
        on_conflict="name", ignore_duplicates=True).execute()
    t.table("payment_methods").upsert(
        [{"name": n, "sort_order": i + 1} for i, n in enumerate(DEFAULT_PAYMENTS)],
        on_conflict="name", ignore_duplicates=True).execute()


# ---- public data API (used by the UI) -----------------------------------
def _clean(df):
    df = df.reindex(columns=EXP_COLS) if not df.empty else pd.DataFrame(columns=EXP_COLS)
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = pd.to_numeric(df["amount"]).astype(float)
    df["id"] = pd.to_numeric(df["id"]).astype("int64")
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_expenses():
    if USE_SUPABASE:
        rows = sb_all(lambda: sb().table("expenses").select("*")
                      .order("date", desc=True).order("id", desc=True))
        df = pd.DataFrame(rows)
    else:
        df = sql_q("SELECT * FROM expenses ORDER BY date DESC, id DESC")
    return _clean(df)


def expenses_on(day):
    df = load_expenses()
    return df[df["date"].dt.date == day].sort_values("id").reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def category_table():
    if USE_SUPABASE:
        df = pd.DataFrame(sb().table("categories").select("name,monthly_budget").execute().data)
    else:
        df = sql_q("SELECT name, monthly_budget FROM categories")
    df["monthly_budget"] = pd.to_numeric(df["monthly_budget"]).fillna(0).astype(float)
    order = {n: i for i, n in enumerate(DEFAULT_CATEGORIES)}
    return df.sort_values("name", key=lambda c: c.map(lambda n: (order.get(n, len(order)), n))) \
             .reset_index(drop=True)


def categories():
    return category_table()["name"].tolist()


@st.cache_data(ttl=300, show_spinner=False)
def payments():
    if USE_SUPABASE:
        names = [r["name"] for r in sb().table("payment_methods").select("name").execute().data]
    else:
        names = sql_q("SELECT name FROM payment_methods")["name"].tolist()
    order = {n: i for i, n in enumerate(DEFAULT_PAYMENTS)}
    return sorted(names, key=lambda n: (order.get(n, len(order)), n))


def _changed():
    load_expenses.clear()
    category_table.clear()
    payments.clear()


def add_expense_row(d, cat, desc, amt, pm):
    if USE_SUPABASE:
        sb().table("expenses").insert({"date": d.isoformat(), "category": cat, "description": desc,
                                       "amount": float(amt), "payment_method": pm}).execute()
    else:
        sql_run("INSERT INTO expenses(date, category, description, amount, payment_method) "
                "VALUES (?,?,?,?,?)", (d.isoformat(), cat, desc, amt, pm))
    _changed()


def update_expense_row(rid, d, cat, desc, amt, pm):
    if USE_SUPABASE:
        sb().table("expenses").update({"date": d.isoformat(), "category": cat, "description": desc,
                                       "amount": float(amt), "payment_method": pm}).eq("id", rid).execute()
    else:
        sql_run("UPDATE expenses SET date=?, category=?, description=?, amount=?, "
                "payment_method=? WHERE id=?", (d.isoformat(), cat, desc, amt, pm, rid))
    _changed()


def delete_expense_row(rid):
    if USE_SUPABASE:
        sb().table("expenses").delete().eq("id", rid).execute()
    else:
        sql_run("DELETE FROM expenses WHERE id=?", (rid,))
    _changed()


def set_budget(name, value):
    if USE_SUPABASE:
        sb().table("categories").update({"monthly_budget": float(value)}).eq("name", name).execute()
    else:
        sql_run("UPDATE categories SET monthly_budget=? WHERE name=?", (float(value), name))


def add_category(name):
    if USE_SUPABASE:
        sb().table("categories").upsert({"name": name}, on_conflict="name",
                                        ignore_duplicates=True).execute()
    else:
        sql_run("INSERT OR IGNORE INTO categories(name) VALUES (?)", (name,))
    _changed()


def add_payment(name):
    if USE_SUPABASE:
        sb().table("payment_methods").upsert({"name": name}, on_conflict="name",
                                             ignore_duplicates=True).execute()
    else:
        sql_run("INSERT OR IGNORE INTO payment_methods(name) VALUES (?)", (name,))
    _changed()


@st.cache_resource(show_spinner=False)
def init_backend():
    if USE_SUPABASE:
        sb_seed_lookups()
    else:
        init_sqlite()
    return True


def tk(x):
    return f"{CURRENCY}{x:,.0f}"


BN_MONTHS = ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই",
             "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]
BN_DAYS = ["সোমবার", "মঙ্গলবার", "বুধবার", "বৃহস্পতিবার", "শুক্রবার", "শনিবার", "রবিবার"]


def bn_month(d):
    """'অক্টোবর 2026' — works for date, Timestamp and Period."""
    return f"{BN_MONTHS[d.month - 1]} {d.year}"


def bn_date(d, year=True):
    return f"{d.day:02d} {BN_MONTHS[d.month - 1]}" + (f" {d.year}" if year else "")


def bn_day(d):
    return BN_DAYS[d.weekday()]


# ---------------------------------------------------------------- styling
FAVICON = Path(__file__).with_name("favicon.png")
st.set_page_config(page_title=APP_NAME, page_icon=str(FAVICON) if FAVICON.exists() else "৳", layout="wide",
                   initial_sidebar_state="collapsed")


def login_gate():
    if not APP_PASSWORD or st.session_state.get("authed"):
        return
    st.markdown("""<style>
      [data-testid="stMain"] .block-container {max-width: 420px; padding-top: 12vh;}
      #MainMenu, footer, header {display:none !important;}
    </style>""", unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;margin-bottom:1.2rem">'
                '<div style="width:56px;height:56px;border-radius:16px;margin:0 auto 12px;display:grid;'
                'place-items:center;color:#fff;font-size:1.6rem;font-weight:700;'
                'background:linear-gradient(135deg,#064E3B,#059669)">৳</div>'
                f'<div style="font-size:1.4rem;font-weight:800">{APP_NAME}</div>'
                '<div style="color:#6B7C74;font-size:.9rem">পাসওয়ার্ড দিয়ে লগইন করুন</div></div>',
                unsafe_allow_html=True)
    with st.form("login"):
        pw = st.text_input("পাসওয়ার্ড", type="password", label_visibility="collapsed",
                           placeholder="পাসওয়ার্ড")
        ok = st.form_submit_button("লগইন", type="primary", width="stretch")
    if ok:
        if hmac.compare_digest(pw.encode(), APP_PASSWORD.encode()):
            st.session_state["authed"] = True
            st.rerun()
        st.error("পাসওয়ার্ড ভুল।")
    st.stop()


login_gate()

try:
    init_backend()
except Exception as e:  # connection problems -> friendly message instead of a traceback
    st.error("**ডাটাবেসে কানেক্ট করা যাচ্ছে না।**  \n"
             + ("`.env` ফাইলের SUPABASE_URL / SUPABASE_KEY চেক করুন, আর ইন্টারনেট কানেকশন আছে কিনা দেখুন।"
                if USE_SUPABASE else "expenses.db ফাইলটা চেক করুন।"))
    st.caption(f"{type(e).__name__}: {e}")
    st.stop()

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Hind+Siliguri:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stApp, button, input, textarea, select
{{font-family: 'Plus Jakarta Sans', 'Hind Siliguri', sans-serif !important;}}
.stApp {{background:
    radial-gradient(1200px 500px at 85% -10%, rgba(5,150,105,.10), transparent 60%),
    radial-gradient(900px 400px at -10% 10%, rgba(16,185,129,.07), transparent 60%), {BG};
    color: {TEXT};}}

/* hide streamlit chrome + sidebar */
#MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], .stDeployButton, section[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"]
{{display: none !important;}}

.block-container {{padding: 1.6rem 2.5rem 3rem; max-width: 1160px;}}

/* brand + nav */
.brand {{display:flex; align-items:center; gap:10px; font-weight:800; font-size:1.15rem;
         color:{TEXT}; letter-spacing:-.02em; white-space:nowrap;}}
.logo {{width:36px; height:36px; border-radius:11px; display:grid; place-items:center;
        color:#fff; font-size:1.15rem; font-weight:700;
        background: linear-gradient(135deg, {DEEP}, {GREEN});
        box-shadow: 0 6px 16px rgba(5,150,105,.30);}}
div[data-testid="stButtonGroup"] {{display:flex; justify-content:flex-end;}}
div[data-testid="stButtonGroup"] > div {{background:{CARD}; border:1px solid {BORDER};
    border-radius:14px; padding:4px; gap:2px; box-shadow:0 2px 8px rgba(11,31,23,.04);}}
div[data-testid="stButtonGroup"] button {{border:none !important; border-radius:10px !important;
    font-weight:600; padding:7px 18px; background:transparent; color:{MUTED};}}
div[data-testid="stButtonGroup"] button[kind="segmented_controlActive"],
div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"]
{{background:{GREEN} !important; color:#fff !important;
  box-shadow:0 4px 12px rgba(5,150,105,.30);}}
div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] *
{{color:#fff !important;}}
.navgap {{height: .8rem;}}
.brand .src {{font-size:.68rem; font-weight:600; color:{GREEN}; background:{MINT}; border:1px solid {GREEN_DIM}; padding:2px 8px; border-radius:999px; letter-spacing:0;}}

h1 {{font-weight:800; letter-spacing:-.035em; font-size:1.75rem !important; color:{TEXT};}}
h3 {{font-weight:700; font-size:.78rem !important; color:{MUTED};
     text-transform:uppercase; letter-spacing:.1em; padding-top:1.1rem !important; padding-bottom:.5rem !important;}}
.pagehead {{font-size:1.35rem; font-weight:800; letter-spacing:-.03em;}}

/* hero */
.hero {{position:relative; overflow:hidden; border-radius:22px; padding:22px 28px;
        color:#fff; background: linear-gradient(125deg, {DEEP} 0%, #047857 55%, {GREEN} 100%);
        box-shadow: 0 18px 40px -18px rgba(6,78,59,.55);
        display:flex; justify-content:space-between; align-items:flex-end; gap:24px; flex-wrap:wrap;}}
.hero:after {{content:""; position:absolute; right:-60px; top:-80px; width:260px; height:260px;
        border-radius:50%; background:rgba(255,255,255,.07);}}
.hero .lbl {{font-size:.8rem; letter-spacing:.1em; text-transform:uppercase; opacity:.75;}}
.hero .big {{font-size:2.4rem; font-weight:800; letter-spacing:-.03em; line-height:1.1; margin-top:6px;}}
.chip {{display:inline-block; margin-top:10px; padding:4px 10px; border-radius:999px;
        font-size:.8rem; font-weight:600; background:rgba(255,255,255,.16);}}
.mini {{display:flex; gap:12px; z-index:1;}}
.mini > div {{background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.16);
        border-radius:14px; padding:12px 16px; min-width:130px; backdrop-filter: blur(4px);}}
.mini .l {{font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; opacity:.75;}}
.mini .v {{font-size:1.2rem; font-weight:700; margin-top:4px;}}

/* panels + rows */
.panel {{background:{CARD}; border:1px solid {BORDER}; border-radius:18px; padding:6px 20px;
         box-shadow:0 2px 10px rgba(11,31,23,.04);}}
.row {{display:flex; align-items:center; gap:14px; padding:13px 0;
       border-bottom:1px solid {BORDER}; font-size:.93rem;}}
.row:last-child {{border-bottom:none;}}
.row .grow {{flex:1; min-width:0;}}
.row .t {{font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}}
.row .d {{color:{MUTED}; font-size:.8rem; margin-top:2px;}}
.row .amt {{font-weight:700; white-space:nowrap;}}
.row .pct {{color:{MUTED}; font-size:.78rem; margin-left:6px; font-weight:500;}}
.ico {{width:40px; height:40px; flex:none; border-radius:12px; display:grid; place-items:center;
       font-size:1.15rem; background:{MINT};}}
.bar {{height:5px; background:#EEF2EF; border-radius:5px; margin-top:8px;}}
.bar > div {{height:100%; border-radius:5px;}}
.empty {{color:{MUTED}; padding:16px 0;}}

/* inputs, buttons, form */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{
    border-radius:12px; font-weight:700; padding:.55rem 1rem;}}
.stFormSubmitButton > button[kind="primaryFormSubmit"], .stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, #047857, {GREEN}); border:none;
    box-shadow:0 8px 20px -8px rgba(5,150,105,.6);}}
div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {{
    border-radius:12px !important;}}
textarea {{font-size:1rem !important; line-height:1.55 !important;}}
div[data-testid="stForm"] {{background:{CARD}; border:1px solid {BORDER}; border-radius:20px;
    padding:1.6rem; box-shadow:0 2px 10px rgba(11,31,23,.04);}}
.stats {{display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:.6rem 0 .4rem;}}
/* glass cards (সব খরচ page) */
.stats > div, .st-key-filterbox, .st-key-daytable {{
    background:linear-gradient(135deg, rgba(255,255,255,.72), rgba(255,255,255,.38)) !important;
    backdrop-filter:blur(16px) saturate(170%); -webkit-backdrop-filter:blur(16px) saturate(170%);
    border:1px solid rgba(255,255,255,.75) !important;
    box-shadow:0 8px 32px rgba(6,78,59,.08), inset 0 1px 0 rgba(255,255,255,.9) !important;}}
.stats > div {{border-radius:16px; padding:14px 18px;}}
.stats .l {{font-size:.72rem; color:{MUTED}; text-transform:uppercase; letter-spacing:.08em;}}
.stats .v {{font-size:1.25rem; font-weight:800; margin-top:4px; white-space:nowrap;
    overflow:hidden; text-overflow:ellipsis;}}
.stats .v.g {{color:{GREEN};}}
.dayhead {{display:flex; justify-content:space-between; margin:1.3rem 4px .5rem;
    font-size:.8rem; font-weight:700; color:{MUTED}; text-transform:uppercase; letter-spacing:.06em;}}
div[class*="st-key-day_dlg"] {{background:{CARD}; border:1px solid {BORDER} !important;
    border-radius:18px !important; box-shadow:0 2px 10px rgba(11,31,23,.04); padding:6px 14px !important;}}
div[class*="st-key-day_dlg"] div[data-testid="stHorizontalBlock"] {{border-bottom:1px solid {BORDER};
    padding:4px 0;}}
div[class*="st-key-day_dlg"] div[data-testid="stHorizontalBlock"]:last-child {{border-bottom:none;}}
div[class*="st-key-day_dlg"] button[kind="tertiary"] {{color:{MUTED}; font-size:1.05rem;
    border-radius:10px; padding:4px 8px;}}
div[class*="st-key-day_dlg"] button[kind="tertiary"]:hover {{background:{MINT}; color:{GREEN};}}
div[data-testid="stDialog"] div[role="dialog"] {{border-radius:20px;}}
.st-key-filterbox {{border-radius:18px !important; padding:16px 20px 20px !important;}}
.st-key-filterbox label p {{font-size:.72rem !important; font-weight:700; color:{MUTED};
    text-transform:uppercase; letter-spacing:.08em;}}
.st-key-filterbox div[data-baseweb="input"], .st-key-filterbox div[data-baseweb="select"] > div {{
    background:rgba(255,255,255,.6) !important; border:1px solid rgba(6,78,59,.10) !important;}}
.st-key-daytable {{border-radius:18px !important; padding:8px !important;}}
.st-key-daytable div[data-testid="stDataFrame"] {{border:none; border-radius:12px; overflow:hidden;}}
.detail {{display:flex; align-items:center; gap:16px; padding:6px 0 16px;}}
.detail .grow {{flex:1; min-width:0;}}
.detail .t {{font-size:1.15rem; font-weight:700;}}
.detail .d {{color:{MUTED}; font-size:.85rem; margin-top:2px;}}
.ico.big {{width:52px; height:52px; font-size:1.5rem; border-radius:16px; display:grid;
    place-items:center; background:{MINT};}}
.amt.big {{font-size:1.6rem; font-weight:800; color:{GREEN};}}
.facts {{display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:10px;}}
.facts > div {{background:#F6F9F7; border:1px solid {BORDER}; border-radius:12px; padding:10px 12px;}}
.facts span {{display:block; font-size:.7rem; color:{MUTED}; text-transform:uppercase; letter-spacing:.08em;}}
.facts b {{display:block; margin-top:3px; font-size:.9rem;}}
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {{border-radius:14px; overflow:hidden;
    border:1px solid {BORDER};}}
/* active nav tab (Streamlit 1.65 uses aria-checked) */
div[data-testid="stButtonGroup"] button[aria-checked="true"]
{{background:{GREEN} !important; color:#fff !important; box-shadow:0 4px 12px rgba(5,150,105,.30);}}
div[data-testid="stButtonGroup"] button[aria-checked="true"] * {{color:#fff !important;}}
div[data-testid="stButtonGroup"] button p {{display:flex; align-items:center; gap:6px; white-space:nowrap;}}
div[data-testid="stButtonGroup"] button [data-testid="stIconMaterial"] {{font-size:1.1rem;}}

/* ============================== MOBILE (phone) ============================== */
@media (max-width: 640px) {{
  .block-container {{padding: .9rem .9rem calc(6.2rem + env(safe-area-inset-bottom)) !important;}}
  .navgap {{height: 0;}}
  .brand {{font-size:1.05rem;}}

  /* bottom tab bar, app style */
  div[data-testid="stButtonGroup"] {{position:fixed; left:0; right:0; bottom:0; z-index:1000;
      padding:6px 8px calc(6px + env(safe-area-inset-bottom));
      background:rgba(255,255,255,.86); backdrop-filter:blur(18px) saturate(180%);
      -webkit-backdrop-filter:blur(18px) saturate(180%);
      border-top:1px solid {BORDER}; box-shadow:0 -8px 28px rgba(6,78,59,.08);}}
  div[data-testid="stButtonGroup"] > div {{width:100%; display:grid !important;
      grid-template-columns:repeat(4, 1fr); gap:4px; background:transparent; border:none;
      box-shadow:none; padding:0; overflow:visible;}}
  div[data-testid="stButtonGroup"] button {{padding:6px 2px !important; min-height:54px; width:100%;
      border-radius:14px !important;}}
  div[data-testid="stButtonGroup"] button span[data-has-shortcut] {{display:flex; flex-direction:column;
      align-items:center; gap:3px;}}
  div[data-testid="stButtonGroup"] button span[data-has-shortcut] > span {{margin:0 !important;}}
  div[data-testid="stButtonGroup"] button p {{font-size:.7rem; line-height:1.2; font-weight:600;}}
  div[data-testid="stButtonGroup"] button [data-testid="stIconMaterial"] {{font-size:1.45rem;}}
  div[data-testid="stButtonGroup"] button[aria-checked="true"] {{background:{MINT} !important;
      box-shadow:none !important;}}
  div[data-testid="stButtonGroup"] button[aria-checked="true"] * {{color:{GREEN} !important;}}

  h1 {{font-size:1.45rem !important;}}
  .pagehead {{font-size:1.2rem;}}
  h3 {{padding-top:.8rem !important;}}

  /* hero */
  .hero {{padding:18px 18px; border-radius:20px; gap:14px;}}
  .hero .big {{font-size:2.05rem;}}
  .hero .lbl {{font-size:.72rem;}}
  .mini {{width:100%; display:grid; grid-template-columns:repeat(3, 1fr); gap:8px;}}
  .mini > div {{min-width:0; padding:10px 10px; border-radius:12px;}}
  .mini .l {{font-size:.62rem; letter-spacing:.04em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}}
  .mini .v {{font-size:.95rem !important; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}}

  /* panels / rows */
  .panel {{padding:4px 14px; border-radius:16px;}}
  .row {{gap:10px; padding:11px 0; font-size:.88rem;}}
  .ico {{width:36px; height:36px; border-radius:10px; font-size:1rem;}}

  /* সব খরচ */
  .stats {{grid-template-columns:repeat(2, 1fr); gap:10px;}}
  .stats > div {{padding:12px 14px;}}
  .stats .v {{font-size:1.15rem;}}
  .st-key-filterbox {{padding:14px 14px 16px !important;}}
  /* filters: date + search full width, category & payment side by side */
  .st-key-filterbox div[data-testid="stHorizontalBlock"] {{flex-wrap:wrap !important; gap:.6rem !important;}}
  .st-key-filterbox div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{
      min-width:calc(50% - .3rem) !important; flex:1 1 calc(50% - .3rem) !important; width:auto !important;}}
  .st-key-filterbox div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(1),
  .st-key-filterbox div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(4) {{
      min-width:100% !important; flex-basis:100% !important;}}
  .st-key-daytable {{padding:4px !important;}}

  /* forms */
  div[data-testid="stForm"] {{padding:1.1rem; border-radius:18px;}}
  input, textarea {{font-size:16px !important;}}   /* stops iOS zoom on focus */

  /* day dialog: keep each transaction row on one line */
  div[data-testid="stDialog"] div[role="dialog"] {{width:100vw !important; max-width:100vw !important;
      margin:0 !important; border-radius:20px 20px 0 0;}}
  div[class*="st-key-day_dlg"] {{padding:4px 10px !important;}}
  div[class*="st-key-day_dlg"] div[data-testid="stHorizontalBlock"]:has(button[kind="tertiary"]) {{
      flex-wrap:nowrap !important; gap:2px !important;}}
  div[class*="st-key-day_dlg"] div[data-testid="stHorizontalBlock"]:has(button[kind="tertiary"]) > div[data-testid="stColumn"] {{
      min-width:0 !important; width:auto !important; flex:0 0 auto !important;}}
  div[class*="st-key-day_dlg"] div[data-testid="stHorizontalBlock"]:has(button[kind="tertiary"]) > div[data-testid="stColumn"]:first-child {{
      flex:1 1 auto !important;}}
  div[class*="st-key-day_dlg"] button[kind="tertiary"] {{padding:4px 6px;}}
}}
</style>
""", unsafe_allow_html=True)

PAGES = ["Dashboard", "Add expense", "Expenses", "Settings"]
PAGE_LABELS = {"Dashboard": ":material/space_dashboard: ড্যাশবোর্ড",
               "Add expense": ":material/add_circle: খরচ যোগ",
               "Expenses": ":material/receipt_long: সব খরচ",
               "Settings": ":material/settings: সেটিংস"}
n1, n2 = st.columns([1, 2], vertical_alignment="center")
n1.markdown(f'<div class="brand"><div class="logo">৳</div>{APP_NAME}'
            f'<span class="src">{"☁️ Supabase" if USE_SUPABASE else "💾 লোকাল"}</span></div>',
            unsafe_allow_html=True)
# tapping the already-open tab would deselect it -> keep the last page selected
if st.session_state.get("page") is None and st.session_state.get("last_page"):
    st.session_state["page"] = st.session_state["last_page"]
page = n2.segmented_control("nav", PAGES, default="Dashboard", key="page",
                            format_func=lambda p: PAGE_LABELS.get(p, p),
                            label_visibility="collapsed") or "Dashboard"
st.session_state["last_page"] = page
st.markdown('<div class="navgap"></div>', unsafe_allow_html=True)


def panel(html, fill=False):
    st.markdown(f'<div class="panel{" fill" if fill else ""}">'
                f'{html or "<div class=empty>কোনো তথ্য নেই</div>"}</div>', unsafe_allow_html=True)


def tx_rows(frame):
    return "".join(
        f'<div class="row"><div class="ico">{CAT_ICON.get(r.category, "•")}</div>'
        f'<div class="grow"><div class="t">{r.description or r.category}</div>'
        f'<div class="d">{bn_date(r.date, year=False)} · {r.category} · {r.payment_method}</div></div>'
        f'<div class="amt">{tk(r.amount)}</div></div>' for r in frame.itertuples())


# ---------------------------------------------------------------- dashboard
def dashboard():
    df = load_expenses()
    today = pd.Timestamp(bd_today())
    df["period"] = df["date"].dt.to_period("M")
    months = sorted(df["period"].unique(), reverse=True)
    if today.to_period("M") not in months:
        months.insert(0, today.to_period("M"))

    st.markdown("""<style>
    @media (min-width: 641px) {
    [data-testid="stMain"], [data-testid="stAppViewContainer"], .stApp {overflow: hidden !important;}
    .block-container {padding-top: 1.2rem !important; padding-bottom: 0 !important;}
    .fill {height: calc(100vh - 400px); min-height: 160px; overflow-y: auto;}
    .fill::-webkit-scrollbar {width: 6px;} .fill::-webkit-scrollbar-thumb {background:#D5DED8; border-radius:6px;}
    }
    </style>""", unsafe_allow_html=True)

    h1, h2 = st.columns([3, 1], vertical_alignment="center")
    h1.markdown(f'<div class="pagehead">সারসংক্ষেপ</div>', unsafe_allow_html=True)
    sel = h2.selectbox("মাস", months, format_func=bn_month,
                       label_visibility="collapsed")

    mdf, prev = df[df["period"] == sel], df[df["period"] == sel - 1]
    m_total, p_total = mdf["amount"].sum(), prev["amount"].sum()
    days = today.day if sel == today.to_period("M") else sel.days_in_month

    if p_total:
        pct = (m_total - p_total) / p_total * 100
        chip = f'{"▲" if pct > 0 else "▼"} গত মাসের চেয়ে {abs(pct):.0f}% {"বেশি" if pct > 0 else "কম"}'
    else:
        chip = f"{len(mdf)}টি লেনদেন"
    today_amt = df.loc[df["date"] == today, "amount"].sum()

    st.markdown(f"""
    <div class="hero">
      <div style="z-index:1">
        <div class="lbl">{bn_month(sel)} · মোট খরচ</div>
        <div class="big">{tk(m_total)}</div>
        <div class="chip">{chip}</div>
      </div>
      <div class="mini">
        <div><div class="l">আজ</div><div class="v">{tk(today_amt)}</div></div>
        <div><div class="l">দৈনিক গড়</div><div class="v">{tk(m_total / max(days, 1))}</div></div>
        <div><div class="l">গত মাস</div><div class="v">{tk(p_total)}</div></div>
      </div>
    </div>""", unsafe_allow_html=True)

    ct = category_table()
    budget = dict(zip(ct["name"], ct["monthly_budget"]))
    budget = {k: v for k, v in budget.items() if v > 0}

    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("ক্যাটাগরি অনুযায়ী")
        cat = mdf.groupby("category")["amount"].sum().sort_values(ascending=False)
        rows = ""
        for name, amt in cat.items():
            if name in budget:
                ratio = amt / budget[name]
                color = RED if ratio > 1 else AMBER if ratio > .8 else GREEN
                right_txt = f'{tk(amt)}<span class="pct">/ {tk(budget[name])}</span>'
            else:
                ratio, color = amt / m_total, GREEN
                right_txt = f'{tk(amt)}<span class="pct">{ratio * 100:.0f}%</span>'
            rows += (f'<div class="row"><div class="ico">{CAT_ICON.get(name, "•")}</div>'
                     f'<div class="grow"><div style="display:flex;justify-content:space-between">'
                     f'<span class="t">{name}</span><span class="amt">{right_txt}</span></div>'
                     f'<div class="bar"><div style="width:{min(ratio, 1) * 100:.0f}%;'
                     f'background:{color}"></div></div></div></div>')
        panel(rows, fill=True)

    with right:
        st.subheader("সাম্প্রতিক")
        panel(tx_rows(mdf.head(20)), fill=True)


# ---------------------------------------------------------------- add
def add_expense():
    st.title("খরচ যোগ করুন")
    with st.form("add", clear_on_submit=True):
        c1, c2 = st.columns(2)
        amt = c1.number_input(f"পরিমাণ ({CURRENCY})", min_value=0.0, step=10.0, format="%.0f")
        d = c2.date_input("তারিখ", bd_today())
        cat = c1.selectbox("ক্যাটাগরি", categories(), format_func=lambda n: f"{CAT_ICON.get(n, '•')}  {n}")
        pms = payments()
        pm = c2.selectbox("পেমেন্ট মাধ্যম", pms, index=pms.index("ক্যাশ") if "ক্যাশ" in pms else 0)
        desc = st.text_area("বিবরণ", placeholder="যেমন: মাছ ১ কেজি, সবজি, বাইকের তেল", height=130)
        if st.form_submit_button("খরচ সেভ করুন", type="primary", width="stretch"):
            if amt <= 0:
                st.error("পরিমাণ ০-এর বেশি হতে হবে।")
            else:
                add_expense_row(d, cat, desc.strip(), amt, pm)
                st.toast(f"সেভ হয়েছে {tk(amt)} · {desc or cat}")

    st.subheader("সাম্প্রতিক")
    recent = load_expenses().head(6)
    panel(tx_rows(recent))


# ---------------------------------------------------------------- list / edit
def reset_table():
    st.session_state["tbl_v"] = st.session_state.get("tbl_v", 0) + 1
    st.session_state["opened_day"] = None
    st.session_state["edit_id"] = None
    st.session_state["del_id"] = None


def set_state(**kw):
    for k, v in kw.items():
        st.session_state[k] = v


@st.dialog("লেনদেন", width="large", on_dismiss=reset_table)
def day_dialog(day):
    tx = expenses_on(day)
    if msg := st.session_state.pop("dlg_flash", None):
        st.success(msg)
    total = tx["amount"].sum()
    if tx.empty:
        hi_txt, top_txt, pay_txt = "—", "—", "—"
    else:
        hi = tx.loc[tx["amount"].idxmax()]
        hi_txt = tk(hi["amount"])
        top = tx.groupby("category")["amount"].sum().idxmax()
        top_txt = f'{CAT_ICON.get(top, "")} {top}'
        pay_txt = tx["payment_method"].mode().iat[0]
    st.markdown(f"""
    <div class="hero" style="padding:20px 26px">
      <div style="z-index:1">
        <div class="lbl">{bn_date(day)} · {bn_day(day)}</div>
        <div class="big">{tk(total)}</div>
        <div class="chip">{len(tx)}টি লেনদেন</div>
      </div>
      <div class="mini">
        <div><div class="l">সর্বোচ্চ</div><div class="v">{hi_txt}</div></div>
        <div><div class="l">শীর্ষ ক্যাটাগরি</div><div class="v" style="font-size:1rem">{top_txt}</div></div>
        <div><div class="l">বেশিরভাগ পেমেন্ট</div><div class="v" style="font-size:1rem">{pay_txt}</div></div>
      </div>
    </div>""", unsafe_allow_html=True)

    if tx.empty:
        st.markdown('<div class="panel" style="margin-top:14px"><div class="empty">এই দিনে আর কোনো এন্ট্রি নেই।</div></div>',
                    unsafe_allow_html=True)
        return

    left, right = st.columns([2, 3], gap="large")
    with left:
        st.subheader("ক্যাটাগরি অনুযায়ী")
        cat = tx.groupby("category")["amount"].sum().sort_values(ascending=False)
        rows = "".join(
            f'<div class="row"><div class="ico">{CAT_ICON.get(n, "•")}</div>'
            f'<div class="grow"><div style="display:flex;justify-content:space-between">'
            f'<span class="t">{n}</span><span class="amt">{tk(a)}<span class="pct">{a / total * 100:.0f}%</span></span></div>'
            f'<div class="bar"><div style="width:{a / total * 100:.0f}%;background:{GREEN}"></div></div></div></div>'
            for n, a in cat.items())
        panel(rows)

    with right:
        cats, pms = categories(), payments()
        edit_id, del_id = st.session_state.get("edit_id"), st.session_state.get("del_id")
        st.subheader("লেনদেন")
        with st.container(border=True, key="day_dlg"):
            for r in tx.to_dict("records"):
                rid = int(r["id"])
                if rid == edit_id:
                    with st.form(f"f{rid}", border=False):
                        c1, c2 = st.columns(2)
                        amt = c1.number_input(f"পরিমাণ ({CURRENCY})", min_value=1.0,
                                              value=float(r["amount"]), step=10.0, format="%.0f")
                        d = c2.date_input("তারিখ", pd.Timestamp(r["date"]).date())
                        cat = c1.selectbox("ক্যাটাগরি", cats,
                                           index=cats.index(r["category"]) if r["category"] in cats else 0,
                                           format_func=lambda n: f"{CAT_ICON.get(n, '•')}  {n}")
                        pm = c2.selectbox("পেমেন্ট মাধ্যম", pms,
                                          index=pms.index(r["payment_method"]) if r["payment_method"] in pms else 0)
                        desc = st.text_area("বিবরণ", r["description"] or "", height=90)
                        b1, b2 = st.columns(2)
                        if b1.form_submit_button("বাতিল", width="stretch"):
                            set_state(edit_id=None)
                            st.rerun(scope="fragment")
                        if b2.form_submit_button("সেভ", type="primary", width="stretch"):
                            update_expense_row(rid, d, cat, desc.strip(), amt, pm)
                            set_state(edit_id=None, dlg_flash="আপডেট হয়েছে ✓")
                            st.rerun(scope="fragment")
                    continue

                cols = st.columns([10, 2.4, .8, .8], vertical_alignment="center", gap="small")
                cols[0].markdown(
                    f'<div class="row" style="border:none;padding:4px 0">'
                    f'<div class="ico">{CAT_ICON.get(r["category"], "•")}</div>'
                    f'<div class="grow"><div class="t">{r["description"] or r["category"]}</div>'
                    f'<div class="d">{r["category"]} · {r["payment_method"]}</div></div></div>',
                    unsafe_allow_html=True)
                if rid == del_id:
                    cols[1].markdown('<div class="d" style="text-align:right;color:#DC2626">মুছবেন?</div>',
                                     unsafe_allow_html=True)
                    if cols[2].button("✓", key=f"y{rid}", type="tertiary", help="হ্যাঁ, মুছুন"):
                        delete_expense_row(rid)
                        set_state(del_id=None, dlg_flash="মুছে ফেলা হয়েছে ✓")
                        st.rerun(scope="fragment")
                    if cols[3].button("✕", key=f"n{rid}", type="tertiary", help="বাতিল"):
                        set_state(del_id=None)
                        st.rerun(scope="fragment")
                else:
                    cols[1].markdown(f'<div class="amt" style="text-align:right">{tk(r["amount"])}</div>',
                                     unsafe_allow_html=True)
                    if cols[2].button("✎", key=f"e{rid}", type="tertiary", help="এডিট"):
                        set_state(edit_id=rid, del_id=None)
                        st.rerun(scope="fragment")
                    if cols[3].button("🗑", key=f"d{rid}", type="tertiary", help="মুছুন"):
                        set_state(del_id=rid, edit_id=None)
                        st.rerun(scope="fragment")


def all_expenses():
    df = load_expenses()

    h1, h2 = st.columns([3, 1], vertical_alignment="center")
    h1.title("সব খরচ")
    if df.empty:
        st.markdown('<div class="panel"><div class="empty">এখনো কোনো খরচ নেই।</div></div>',
                    unsafe_allow_html=True)
        return

    fbox = st.container(border=True, key="filterbox")
    c1, c2, c3, c4 = fbox.columns([2.2, 2, 2, 2.6])
    dr = c1.date_input("তারিখের সীমা", (df["date"].min().date(), df["date"].max().date()))
    cats = c2.multiselect("ক্যাটাগরি", categories(), placeholder="সব")
    pmf = c3.multiselect("পেমেন্ট", payments(), placeholder="সব")
    search = c4.text_input("খুঁজুন", placeholder="🔍  বিবরণে খুঁজুন")

    f = df
    if isinstance(dr, tuple) and len(dr) == 2:
        f = f[(f["date"] >= pd.Timestamp(dr[0])) & (f["date"] <= pd.Timestamp(dr[1]))]
    if cats:
        f = f[f["category"].isin(cats)]
    if pmf:
        f = f[f["payment_method"].isin(pmf)]
    if search:
        f = f[f["description"].fillna("").str.contains(search, case=False, regex=False)]

    export = f.assign(date=f["date"].dt.date).drop(columns=["created_at"], errors="ignore")
    h2.download_button("⬇  CSV এক্সপোর্ট", export.to_csv(index=False).encode("utf-8-sig"),
                       "expenses.csv", "text/csv", width="stretch")

    days = (f.groupby(f["date"].dt.date)
             .agg(entries=("id", "count"), total=("amount", "sum"))
             .sort_index(ascending=False).reset_index())
    st.markdown(f"""
    <div class="stats">
      <div><div class="l">দিন</div><div class="v">{len(days)}</div></div>
      <div><div class="l">এন্ট্রি</div><div class="v">{len(f)}</div></div>
      <div><div class="l">মোট</div><div class="v g">{tk(f['amount'].sum())}</div></div>
      <div><div class="l">দৈনিক গড়</div><div class="v">{tk(days['total'].mean() if len(days) else 0)}</div></div>
    </div>""", unsafe_allow_html=True)
    st.caption("যেকোনো তারিখে ক্লিক করলে সেই দিনের সব লেনদেন খুলবে — সেখান থেকে এডিট বা মুছে ফেলতে পারবেন।")

    if days.empty:
        st.markdown('<div class="panel"><div class="empty">কোনো এন্ট্রি পাওয়া যায়নি।</div></div>',
                    unsafe_allow_html=True)
        return

    view = pd.DataFrame({
        "তারিখ": days["date"].map(lambda d: bn_date(d, year=d.year != bd_today().year)),
        "বার": days["date"].map(bn_day),
        "এন্ট্রি": days["entries"],
        "পরিমাণ": days["total"],
    })
    event = st.container(border=True, key="daytable").dataframe(
        view, hide_index=True, width="stretch", height=min(35 * len(view) + 38, 600),
        on_select="rerun", selection_mode="single-cell",
        key=f"day_table_{st.session_state.get('tbl_v', 0)}",
        column_config={
            "তারিখ": st.column_config.TextColumn(width=105),
            "বার": st.column_config.TextColumn(width=95),
            "এন্ট্রি": st.column_config.NumberColumn(width=52),
            "পরিমাণ": st.column_config.NumberColumn(format="৳ %,.0f", width=85),
        })

    sel = event.selection
    rows = list(sel.get("rows", [])) or [c[0] for c in sel.get("cells", [])]
    if rows:
        day = days.loc[rows[0], "date"]
        if st.session_state.get("opened_day") != day:
            st.session_state.update(opened_day=day, edit_id=None, del_id=None)
        day_dialog(day)
    else:
        st.session_state["opened_day"] = None


# ---------------------------------------------------------------- settings
def settings():
    st.title("সেটিংস")
    src = "☁️ Supabase" if USE_SUPABASE else "💾 লোকাল (expenses.db)"
    st.markdown(f'<div class="chip" style="background:{MINT};color:{GREEN};margin:0 0 .4rem">'
                f'ডাটাবেস: {src}</div>', unsafe_allow_html=True)

    st.subheader("মাসিক বাজেট")
    st.caption("যে ক্যাটাগরির বাজেট লাগবে না, সেখানে ০ রাখুন।")
    b = category_table().rename(columns={"name": "category"})
    eb = st.data_editor(b, hide_index=True, width="stretch", disabled=["category"],
                        column_config={"category": "ক্যাটাগরি",
                                       "monthly_budget": st.column_config.NumberColumn(
                                           f"বাজেট ({CURRENCY})", min_value=0, step=500)})
    if st.button("বাজেট সেভ করুন", type="primary"):
        old = dict(zip(b["category"], b["monthly_budget"]))
        for r in eb.itertuples():
            new_val = float(r.monthly_budget or 0)
            if new_val != old.get(r.category):
                set_budget(r.category, new_val)
        category_table.clear()
        st.toast("বাজেট সেভ হয়েছে")

    st.subheader("নতুন যোগ করুন")
    c1, c2 = st.columns(2)
    nc = c1.text_input("নতুন ক্যাটাগরি")
    if c1.button("ক্যাটাগরি যোগ করুন") and nc.strip():
        add_category(nc.strip())
        st.toast(f"যোগ হয়েছে: {nc}")
    npm = c2.text_input("নতুন পেমেন্ট মাধ্যম")
    if c2.button("পেমেন্ট মাধ্যম যোগ করুন") and npm.strip():
        add_payment(npm.strip())
        st.toast(f"যোগ হয়েছে: {npm}")

    st.subheader("ব্যাকআপ")
    all_df = load_expenses()
    backup = all_df.assign(date=all_df["date"].dt.date).to_csv(index=False).encode("utf-8-sig")
    c1, c2, _ = st.columns([1, 1, 2])
    c1.download_button("⬇  সব খরচ (CSV)", backup, f"expenses-backup-{bd_today()}.csv",
                       "text/csv", width="stretch")
    if not USE_SUPABASE and DB_PATH.exists():
        c2.download_button("⬇  expenses.db", DB_PATH.read_bytes(), "expenses.db", width="stretch")
    if c2.button("↻  ডাটা রিফ্রেশ", width="stretch") if USE_SUPABASE else False:
        _changed()
        st.rerun()


{"Dashboard": dashboard, "Add expense": add_expense,
 "Expenses": all_expenses, "Settings": settings}[page]()
