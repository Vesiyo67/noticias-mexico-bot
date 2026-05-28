import os, requests, sqlite3, logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
NEWS_KEY = os.getenv("NEWS_API_KEY")

DB_FILE = "noticias.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS noticias (
            url TEXT PRIMARY KEY, titulo TEXT, categoria TEXT, fuente TEXT,
            fecha TEXT, resumen TEXT, enviado INTEGER DEFAULT 0)''')

CATEGORIAS = {
    "Política": ["presidente", "senado", "diputados", "gobierno", "ley", "electoral", "partido", "congreso", "sheinbaum", "amlo"],
    "Economía": ["peso", "inflación", "banxico", "bolsa", "empresas", "inversión", "turismo", "comercio", "petróleo", "dólar"],
    "Tecnología": ["ia", "inteligencia artificial", "ciberseguridad", "startup", "tech", "software", "digital", "5g"],
    "Deportes": ["fútbol", "selección", "liga mx", "olímpicos", "box", "fórmula", "deportivo", "campeonato", "chivas", "américa"],
    "Sociedad": ["seguridad", "educación", "salud", "migrantes", "clima", "desastre", "protesta", "comunidad", "violencia"]
}

def obtener_categoria(titulo, desc=""):
    texto = f"{titulo} {desc}".lower()
    for cat, palabras in CATEGORIAS.items():
        if any(p in texto for p in palabras):
            return cat
    return "General"

obtener_noticias()

def resumen_inteligente(desc, titulo):
    if not desc: return titulo[:90] + "..."
    return desc.split(".")[0].strip() + "."

URGENCIA = ["urgente", "última hora", "alerta", "sismo", "rompe", "exclusiva", "emergencia", "tragedia", "ataque", "tiroteo"]
def es_urgente(titulo, desc=""):
    return any(p in f"{titulo} {desc}".lower() for p in URGENCIA)

def enviar_telegram(texto):
    try:
        r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        logging.error(f"Error Telegram: {e}")
        return False

def digest_diario():
    print("📅 Generando digest diario...")
    noticias = obtener_noticias()
    if not noticias:
        enviar_telegram("⚠️ No se pudieron obtener noticias hoy.")
        return

    hoy = datetime.now().strftime("%A, %d de %B")
    msg = f"🇲🇽 *Noticias México - {hoy}*\n\n"
    
    for i, n in enumerate(noticias[:5], 1):
        cat = obtener_categoria(n["title"], n.get("description", ""))
        resumen = resumen_inteligente(n.get("description", ""), n["title"])
        fuente = n.get("source", {}).get("name", "N/A")
        msg += f"🔹 *{i}. [{cat}] {n['title']}*\n📝 {resumen}\n📰 {fuente} | 🔗 [Abrir]({n['url']})\n\n"
        
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT OR IGNORE INTO noticias (url, titulo, categoria, fuente, fecha, resumen) VALUES (?,?,?,?,?,?)",
                         (n["url"], n["title"], cat, fuente, datetime.now().strftime("%Y-%m-%d"), resumen))
            
    msg += "_📁 Historial guardado automáticamente | Enviado por tu Agente 🤖_"
    enviar_telegram(msg)
    print("✅ Digest enviado")

def revisar_urgentes():
    print("🔍 Revisando urgentes...")
    noticias = obtener_noticias()
    hoy = datetime.now().strftime("%Y-%m-%d")
    
    for n in noticias:
        url = n.get("url", "")
        if not url: continue
        
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.execute("SELECT 1 FROM noticias WHERE url=? AND fecha=?", (url, hoy))
            if cur.fetchone(): continue
            
        if es_urgente(n["title"], n.get("description", "")):
            cat = obtener_categoria(n["title"], n.get("description", ""))
            fuente = n.get("source", {}).get("name", "N/A")
            msg = (f"🚨 *ALERTA URGENTE*\n📰 {n['title']}\n🗂️ {cat} • {fuente}\n"
                   f"🕐 {datetime.now().strftime('%H:%M')}\n🔗 [Ver]({url})")
            enviar_telegram(msg)
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT OR IGNORE INTO noticias (url, titulo, categoria, fuente, fecha, resumen, enviado) VALUES (?,?,?,?,?,?,1)",
                             (url, n["title"], cat, fuente, hoy, n.get("description","")[:100]))
            print("✅ Alerta enviada")

if __name__ == "__main__":
    init_db()
    digest_diario()
