from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import swisseph as swe
import pytz

# -----------------------------------------------------------------------------
# APP INITIALIZATION
# -----------------------------------------------------------------------------
app = FastAPI(
    title="AajKyaHai Astro API",
    version="1.1",
    description="Swiss Ephemeris based Astronomy API for Rashifal & Panchang"
)

# -----------------------------------------------------------------------------
# CORS (MANDATORY FOR WORDPRESS ADMIN + BROWSER CALLS)
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Allow WP admin & frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# SWISS EPHEMERIS SETUP (FULL PRECISION)
# -----------------------------------------------------------------------------
# IMPORTANT: ephe folder must contain sepl_18.se1 & semo_18.se1
swe.set_ephe_path("./ephe")

# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------
SIGNS = [
    ("मेष", "Aries"),
    ("वृषभ", "Taurus"),
    ("मिथुन", "Gemini"),
    ("कर्क", "Cancer"),
    ("सिंह", "Leo"),
    ("कन्या", "Virgo"),
    ("तुला", "Libra"),
    ("वृश्चिक", "Scorpio"),
    ("धनु", "Sagittarius"),
    ("मकर", "Capricorn"),
    ("कुंभ", "Aquarius"),
    ("मीन", "Pisces"),
]

NAKSHATRAS = [
    ("अश्विनी","Ashwini"),("भरणी","Bharani"),("कृत्तिका","Krittika"),
    ("रोहिणी","Rohini"),("मृगशिरा","Mrigashira"),("आर्द्रा","Ardra"),
    ("पुनर्वसु","Punarvasu"),("पुष्य","Pushya"),("आश्लेषा","Ashlesha"),
    ("मघा","Magha"),("पूर्व फाल्गुनी","Purva Phalguni"),
    ("उत्तर फाल्गुनी","Uttara Phalguni"),("हस्त","Hasta"),
    ("चित्रा","Chitra"),("स्वाती","Swati"),("विशाखा","Vishakha"),
    ("अनुराधा","Anuradha"),("ज्येष्ठा","Jyeshtha"),
    ("मूल","Mula"),("पूर्वाषाढ़ा","Purva Ashadha"),
    ("उत्तराषाढ़ा","Uttara Ashadha"),("श्रवण","Shravana"),
    ("धनिष्ठा","Dhanishta"),("शतभिषा","Shatabhisha"),
    ("पूर्व भाद्रपद","Purva Bhadrapada"),
    ("उत्तर भाद्रपद","Uttara Bhadrapada"),
    ("रेवती","Revati"),
]

TITHIS = [
    ("प्रतिपदा","Pratipada"),("द्वितीया","Dwitiya"),("तृतीया","Tritiya"),
    ("चतुर्थी","Chaturthi"),("पंचमी","Panchami"),("षष्ठी","Shashthi"),
    ("सप्तमी","Saptami"),("अष्टमी","Ashtami"),("नवमी","Navami"),
    ("दशमी","Dashami"),("एकादशी","Ekadashi"),("द्वादशी","Dwadashi"),
    ("त्रयोदशी","Trayodashi"),("चतुर्दशी","Chaturdashi"),
    ("पूर्णिमा","Purnima"),
]

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def zodiac_from_longitude(lon: float):
    index = int(lon // 30) % 12
    return SIGNS[index]

def nakshatra_from_longitude(lon: float):
    index = int(lon // (360 / 27)) % 27
    return NAKSHATRAS[index]

def tithi_from_longitudes(sun_lon: float, moon_lon: float):
    diff = (moon_lon - sun_lon) % 360.0
    tithi_no = int(diff // 12.0)  # 0..29
    paksha_hi = "शुक्ल" if tithi_no < 15 else "कृष्ण"
    tithi = TITHIS[tithi_no % 15]
    return f"{paksha_hi} {tithi[0]}", f"{paksha_hi} {tithi[1]}"

# -----------------------------------------------------------------------------
# HEALTH CHECK (FOR RENDER + CRON)
# -----------------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return {"ok": True, "service": "astro-api"}

# -----------------------------------------------------------------------------
# MAIN ASTRO ENDPOINT
# -----------------------------------------------------------------------------
@app.get("/astro")
def astro(
    date: str = Query(..., description="YYYY-MM-DD", example="2026-02-06"),
    tz: str = Query("Asia/Kolkata"),
    lat: float = Query(28.6139),
    lon: float = Query(77.2090),
):
    """
    Returns astronomy-based data (NOT AI):
    - Sun sign
    - Moon sign
    - Tithi
    - Nakshatra
    """

    # Use 06:00 IST to represent the day consistently
    local_tz = pytz.timezone(tz)
    dt_local = local_tz.localize(
        datetime.strptime(date, "%Y-%m-%d") + timedelta(hours=6)
    )

    # Convert to UTC for Swiss Ephemeris
    dt_utc = dt_local.astimezone(pytz.UTC)

    jd_ut = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    )

    # Planetary positions
    sun_lon = swe.calc_ut(jd_ut, swe.SUN)[0][0]
    moon_lon = swe.calc_ut(jd_ut, swe.MOON)[0][0]

    sun_hi, sun_en = zodiac_from_longitude(sun_lon)
    moon_hi, moon_en = zodiac_from_longitude(moon_lon)

    nak_hi, nak_en = nakshatra_from_longitude(moon_lon)
    tithi_hi, tithi_en = tithi_from_longitudes(sun_lon, moon_lon)

    return {
        "date": date,
        "timezone": tz,
        "sun": {
            "longitude": round(sun_lon, 6),
            "sign_hi": sun_hi,
            "sign_en": sun_en
        },
        "moon": {
            "longitude": round(moon_lon, 6),
            "sign_hi": moon_hi,
            "sign_en": moon_en
        },
        "panchang": {
            "tithi": {
                "hi": tithi_hi,
                "en": tithi_en
            },
            "nakshatra": {
                "hi": nak_hi,
                "en": nak_en
            }
        }
    }
