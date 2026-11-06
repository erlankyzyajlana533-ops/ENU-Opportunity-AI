import base64
from pathlib import Path
import streamlit as st


def apply_design():
    image_path = Path(__file__).resolve().parent / 'assets' / 'enu_building.png'
    photo = ''
    if image_path.exists():
        photo = base64.b64encode(image_path.read_bytes()).decode('ascii')
    background = f'linear-gradient(90deg, rgba(5,30,85,.91), rgba(8,76,160,.36)), url("data:image/png;base64,{photo}")' if photo else 'linear-gradient(110deg,#052457,#1671d9)'
    st.markdown('''<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"], [data-testid="stApp"] {font-family:Manrope,Arial,sans-serif;}
    [data-testid="stApp"] {background:linear-gradient(120deg,#e8f3ff,#f8fbff 52%,#d8ebff);}
    [data-testid="stApp"]::before {content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background:radial-gradient(circle at 20% 70%,rgba(0,180,255,.17),transparent 34%),radial-gradient(circle at 85% 20%,rgba(37,99,235,.15),transparent 35%);animation:ambient 13s ease-in-out infinite alternate;}
    @keyframes ambient {from {transform:translate3d(-2%,1%,0) scale(1)}to {transform:translate3d(2%,-2%,0) scale(1.08)}}
    [data-testid="stMainBlockContainer"] {position:relative;z-index:1;max-width:1250px;padding-top:1.5rem;}
    [data-testid="stSidebar"] {background:linear-gradient(165deg,#061c47,#0750a6 80%,#083778);}
    [data-testid="stSidebar"] * {color:#f5faff!important;}
    h1,h2,h3 {color:#102a56!important;letter-spacing:-.025em;}
    div[data-testid="stButton"] button[kind="primary"] {background:linear-gradient(100deg,#0860e8,#12a4f5);color:white;border:0;box-shadow:0 7px 20px #0871d63b;}
    div[data-testid="stButton"] button {border-radius:12px;transition:transform .2s,box-shadow .2s;}
    div[data-testid="stButton"] button:hover {transform:translateY(-2px);box-shadow:0 8px 20px #0861bb35;}
    div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:18px;}
    input, textarea {border-radius:10px!important;}
    @media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
    </style>''', unsafe_allow_html=True)
    st.markdown(f'''<section style='position:relative;overflow:hidden;min-height:250px;padding:34px 38px;border-radius:24px;background:{background};background-position:center;background-size:cover;color:white;box-shadow:0 18px 38px #083a8535'>
      <div style='position:relative;z-index:1;max-width:750px'>
      <div style='font-size:13px;letter-spacing:2px;font-weight:800;color:#c5e9ff'>L.N. GUMILYOV EURASIAN NATIONAL UNIVERSITY</div>
      <div style='font-size:clamp(28px,4vw,48px);font-weight:800;line-height:1.15;margin:16px 0 10px'>Біз алмайтын асу жоқ!</div>
      <div style='font-size:17px;font-weight:600;color:#e7f4ff'>🎓 ENU Opportunity AI</div>
      <div style='font-size:14px;margin-top:10px;color:#e4efff'>Ғылыми жетекші мен студентті интеллектуалды сәйкестендіру платформасы</div>
      </div>
      <div style='position:absolute;bottom:-60px;right:-60px;width:240px;height:240px;border:2px solid #9de6ff70;border-radius:50%;box-shadow:0 0 65px #00c8ff70;animation:floatRing 8s ease-in-out infinite alternate'></div>
    </section><style>@keyframes floatRing{{to{{transform:translate(-35px,-30px) scale(1.12)}}}}</style>''', unsafe_allow_html=True)
    st.write('')
