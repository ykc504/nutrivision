"""Main FastAPI application for NutriVision AI platform.

Practical MVP:
 - Onboarding -> personalized targets (BMR/TDEE)
 - Barcode scan -> Open Food Facts (+ USDA fallback)
 - Food diary + water tracking (SQLite)
 - Photo meal scan (free local model if available) + manual fallback
 - Free AI coach (local HF model if available; rule-based fallback)
"""

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
import uvicorn
import os
import json
from dotenv import load_dotenv

# Load .env early so database + AI keys are available everywhere.
load_dotenv()

from passlib.context import CryptContext
from starlette.middleware.sessions import SessionMiddleware

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Import services
from database import (
    init_database,
    get_user_profile,
    save_user_profile,
    get_food_logs,
    save_food_log,
    get_cached_product,
    cache_product,
    save_water_log,
    get_water_logs,
    get_day_totals,
    create_user,
    get_user_by_email,
    get_user_by_id,
)
from services.bmr import calculate_user_targets
from services.food_api import fetch_product, search_products, get_sample_products
from services.usda_api import fallback_nutrition_for_name
from services.scoring import compute_personalized_score
from services.disease_scores import scores_for_conditions
from services.additive_engine import classify_additives, detect_harmful_chemicals, get_additive_summary
from services.microplastics import detect_microplastics_risk
from services.health_score import calculate_health_score, get_weekly_stats, generate_daily_insight
from services.ai_coach import generate_coach_response
from services.who_guidelines import day_guideline_warnings

# New differentiators
from services.risk_index import compute_daily_risk
from services.reporting import build_weekly_pdf
from services.menu_ocr import ocr_menu_items, recommend_menu_items
from services.swaps import find_swaps
from services.simulator import simulate_daily
from database import create_grocery_session, add_grocery_item, get_grocery_items, end_grocery_session

# Initialize FastAPI app
app = FastAPI(title="NutriVision AI", version="1.0.0")
# Session cookie signing key. Keep stable across restarts or users will be logged out.
# Prefer SECRET_KEY in .env, fall back to SESSION_SECRET, then a dev default.
_session_key = os.getenv("SECRET_KEY") or os.getenv("SESSION_SECRET") or "nutrivision-dev-secret"
app.add_middleware(
    SessionMiddleware,
    secret_key=_session_key,
    same_site="lax",
)


# Setup templates and static files

def _uid(request: Request) -> int | None:
    return request.session.get("uid")

def _require_user(request: Request) -> int | None:
    uid = _uid(request)
    return uid

def _hash_password(pw: str) -> str:
    return pwd_context.hash(pw)

def _verify_password(pw: str, pw_hash: str) -> bool:
    try:
        return pwd_context.verify(pw, pw_hash)
    except Exception:
        return False

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


def _tpl_ctx(request: Request, *, show_nav: bool, active_tab: str | None = None, **extra):
    """Common template context.

    show_nav: hide bottom nav on landing + onboarding.
    active_tab: highlight current tab.
    """
    ctx = {"request": request, "show_nav": show_nav, "active_tab": active_tab}
    ctx.update(extra)
    return ctx

def _build_product_analysis(product, user_profile):
    """Build product analysis with scoring and warnings."""
    score, warnings, recommendation, breakdown = compute_personalized_score(
        product, user_profile
    )
    
    # Analyze additives
    additives_data = classify_additives(product.get('additives', ''))
    additives_summary = get_additive_summary(additives_data)
    harmful_chemicals = detect_harmful_chemicals(product)
    microplastics = detect_microplastics_risk(product)
    
    return {
        'score': score,
        'warnings': warnings,
        'recommendation': recommendation,
        'breakdown': breakdown,
        'additives': additives_data,
        'additives_summary': additives_summary,
        'harmful_chemicals': harmful_chemicals,
        'microplastics': microplastics
    }

static_dir = os.path.join(BASE_DIR, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()
    print("✅ Database initialized")

# Routes
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page."""
    return templates.TemplateResponse("index.html", _tpl_ctx(request, show_nav=False))


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", _tpl_ctx(request, show_nav=False, title="Sign in"))

@app.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    user = get_user_by_email(email)
    if not user or not _verify_password(password, user["password_hash"]):
        return templates.TemplateResponse("login.html", _tpl_ctx(request, show_nav=False, title="Sign in", error="Invalid email or password."))
    uid = int(user["id"])
    request.session["uid"] = uid
    # If profile already exists, go straight to dashboard.
    if get_user_profile(uid):
        return RedirectResponse("/dashboard", status_code=303)
    return RedirectResponse("/get-started", status_code=303)

@app.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    return templates.TemplateResponse("register.html", _tpl_ctx(request, show_nav=False, title="Create account"))

@app.post("/register")
async def register_post(request: Request, email: str = Form(...), password: str = Form(...)):
    if get_user_by_email(email):
        return templates.TemplateResponse("register.html", _tpl_ctx(request, show_nav=False, title="Create account", error="Email already registered. Please sign in."))
    if len(password) < 6:
        return templates.TemplateResponse("register.html", _tpl_ctx(request, show_nav=False, title="Create account", error="Password must be at least 6 characters."))
    uid = int(create_user(email, _hash_password(password)))
    request.session["uid"] = uid
    return RedirectResponse("/get-started", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.get("/get-started", response_class=HTMLResponse)
async def get_started(request: Request):
    """Onboarding page."""
    uid = _require_user(request)
    if not uid:
        return RedirectResponse('/login', status_code=303)
    return templates.TemplateResponse("onboarding.html", _tpl_ctx(request, show_nav=False))

@app.post("/api/onboarding")
async def save_onboarding(
    request: Request,
    age: int = Form(...),
    gender: str = Form(...),
    height: float = Form(...),
    weight: float = Form(...),
    conditions: str = Form(""),
    goals: str = Form(...),
    activity_level: str = Form(...)
):
    """Save user profile and calculate targets."""
    uid = _require_user(request)
    if not uid:
        return RedirectResponse('/login', status_code=303)
    
    # Calculate nutritional targets
    targets = calculate_user_targets(age, gender, height, weight, activity_level, goals)
    
    # Prepare data for database
    profile_data = {
        'age': age,
        'gender': gender,
        'height': height,
        'weight': weight,
        'conditions': conditions,
        'goals': goals,
        'activity_level': activity_level,
        'calorie_target': targets['calorie_target'],
        'protein_target': targets['protein_target'],
        'carb_target': targets['carb_target'],
        'fat_target': targets['fat_target']
    }

    # Save to database (tie profile to logged-in user)
    save_user_profile(profile_data, uid)
    
    # Redirect to dashboard for a smooth flow
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    uid=_require_user(request)
    if not uid:
        return RedirectResponse('/login', status_code=303)
    user_profile = get_user_profile(uid)
    if not user_profile:
        # Redirect to onboarding if no profile
        return RedirectResponse('/get-started', status_code=303)
    
    today = datetime.now().strftime('%Y-%m-%d')
    logs = get_food_logs(uid, today)
    water_logs = get_water_logs(uid, today)

    totals = get_day_totals(uid, today)
    consumed = {
        'calories': float(totals.get('calories', 0) or 0),
        'protein': float(totals.get('protein', 0) or 0),
        'carbs': float(totals.get('carbs', 0) or 0),
        'fat': float(totals.get('fat', 0) or 0),
        'water_ml': int(totals.get('water_ml', 0) or 0),
    }

    # Progress percentages for ring meters
    def pct(v, t):
        try:
            t = float(t or 0)
            v = float(v or 0)
            return 0 if t <= 0 else max(0, min(100, (v / t) * 100))
        except Exception:
            return 0

    progress = {
        "calories": pct(consumed['calories'], user_profile.get('calorie_target')),
        "protein": pct(consumed['protein'], user_profile.get('protein_target')),
        "carbs": pct(consumed['carbs'], user_profile.get('carb_target')),
        "fat": pct(consumed['fat'], user_profile.get('fat_target')),
        "water": pct(consumed['water_ml'], 2000),  # default 2L/day
    }

    # Health score uses recent week
    logs_week = get_food_logs(uid)  # recent logs
    weekly = get_weekly_stats(logs_week)
    health_score = calculate_health_score(logs_week, user_profile)
    insight = generate_daily_insight(logs, user_profile)

    # Risk exposure index (sugar + sodium + ultra-processed + additives + disease conflicts)
    risk = compute_daily_risk(logs, user_profile)

    conds = (user_profile.get('conditions') or '').lower()
    if 'diabetes' in conds:
        dashboard_mode = 'diabetes'
    elif 'hypertension' in conds:
        dashboard_mode = 'hypertension'
    elif 'pcos' in conds:
        dashboard_mode = 'pcos'
    else:
        dashboard_mode = 'general'

    # WHO guidance (uses sodium/sugar totals if present)
    who = day_guideline_warnings({
        'calories': consumed['calories'],
        'sodium': sum(l.get('sodium', 0) for l in logs),
        'sugar': sum(l.get('sugar', 0) for l in logs),
    }, float(user_profile.get('calorie_target') or 0))

    return templates.TemplateResponse(
        "dashboard.html",
        _tpl_ctx(
            request,
            show_nav=True,
            active_tab="home",
            user=user_profile,
            consumed=consumed,
            logs=logs[:6],
            water_logs=water_logs[:6],
            health_score=health_score,
            risk=risk,
            insight=insight,
            who_warnings=who,
            progress=progress,
            dashboard_mode=dashboard_mode,
        ),
    )

@app.get("/scan", response_class=HTMLResponse)
async def scan_page(request: Request, barcode: str | None = None):
    uid=_require_user(request)
    if not uid:
        return RedirectResponse("/login", status_code=303)

    user_profile = get_user_profile(uid)
    if not user_profile:
        return templates.TemplateResponse("onboarding.html", _tpl_ctx(request, show_nav=False))

    product = None
    analysis = None
    if barcode:
        product = get_cached_product(barcode) or fetch_product(barcode)
        if product:
            cache_product(barcode, product)
            analysis = _build_product_analysis(product, user_profile)

    return templates.TemplateResponse(
        "scan.html",
        _tpl_ctx(request, show_nav=True, active_tab="scan", user=user_profile, product=product, analysis=analysis),
    )





@app.get("/grocery", response_class=HTMLResponse)
async def grocery_page(request: Request, session_id: int | None = None):
    uid=_require_user(request)
    if not uid:
        return RedirectResponse("/login", status_code=303)
    user_profile = get_user_profile(uid)
    if not user_profile:
        return RedirectResponse("/get-started", status_code=303)

    if not session_id:
        session_id = create_grocery_session(uid, "Grocery Session")

    items = get_grocery_items(session_id)
    basket_score = 0
    if items:
        basket_score = round(sum((i.get("score") or 0) for i in items)/len(items))

    return templates.TemplateResponse(
        "grocery.html",
        _tpl_ctx(request, show_nav=True, active_tab="scan", user=user_profile, session_id=session_id, items=items, basket_score=basket_score),
    )

@app.post("/api/grocery/add", response_class=JSONResponse)
async def grocery_add(request: Request, session_id: int = Form(...), barcode: str = Form(...)):
    uid=_require_user(request)
    if not uid:
        return JSONResponse({"ok": False, "error": "auth"}, status_code=401)
    user_profile = get_user_profile(uid)
    product = get_cached_product(barcode) or fetch_product(barcode)
    if not product:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    cache_product(barcode, product)
    score, *_ = compute_personalized_score(product, user_profile)
    add_grocery_item(session_id, product, int(score))
    return JSONResponse({"ok": True})

@app.post("/api/grocery/end", response_class=JSONResponse)
async def grocery_end(request: Request, session_id: int = Form(...)):
    uid=_require_user(request)
    if not uid:
        return JSONResponse({"ok": False, "error": "auth"}, status_code=401)
    end_grocery_session(session_id)
    return JSONResponse({"ok": True})

@app.get("/api/simulate/{barcode}", response_class=JSONResponse)
async def api_simulate(request: Request, barcode: str):
    uid=_require_user(request)
    if not uid:
        return JSONResponse({"ok": False, "error": "auth"}, status_code=401)
    user_profile = get_user_profile(uid)
    product = get_cached_product(barcode) or fetch_product(barcode)
    if not product:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    sim = simulate_daily(product, {"conditions": user_profile.get("conditions","")}, days=30)
    return JSONResponse({"ok": True, "simulation": sim})

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = ""):
    uid=_require_user(request)
    if not uid:
        return RedirectResponse("/login", status_code=303)
    user_profile = get_user_profile(uid)
    if not user_profile:
        return RedirectResponse("/get-started", status_code=303)

    results = []
    if q.strip():
        results = search_products(q.strip(), page_size=12)
    return templates.TemplateResponse(
        "search.html",
        _tpl_ctx(request, show_nav=True, active_tab="scan", title="Search", q=q, results=results, user=user_profile),
    )


@app.get("/meal", response_class=HTMLResponse)
async def meal_page(request: Request):
    uid=_require_user(request)
    if not uid:
        return RedirectResponse('/login', status_code=303)
    user_profile = get_user_profile(uid)
    if not user_profile:
        return RedirectResponse(url="/get-started", status_code=303)
    return templates.TemplateResponse("meal.html", {"request": request, "user": user_profile})


@app.get("/diary", response_class=HTMLResponse)
async def diary_page(request: Request, date: str | None = None):
    uid=_require_user(request)
    if not uid:
        return RedirectResponse('/login', status_code=303)
    user_profile = get_user_profile(uid)
    if not user_profile:
        return RedirectResponse(url="/get-started", status_code=303)
    date = date or datetime.now().strftime('%Y-%m-%d')
    logs = get_food_logs(uid, date)
    water = get_water_logs(uid, date)
    totals = get_day_totals(uid, date)
    return templates.TemplateResponse(
        "diary.html",
        _tpl_ctx(
            request,
            show_nav=True,
            active_tab="diary",
            user=user_profile,
            date=date,
            logs=logs,
            water_logs=water,
            totals=totals,
        ),
    )


@app.get("/coach", response_class=HTMLResponse)
async def coach_page(request: Request):
    uid=_require_user(request)
    if not uid:
        return RedirectResponse('/login', status_code=303)
    user_profile = get_user_profile(uid)
    if not user_profile:
        return RedirectResponse(url="/get-started", status_code=303)
    return templates.TemplateResponse("coach.html", _tpl_ctx(request, show_nav=True, active_tab="coach", user=user_profile))

@app.get("/api/scan/{barcode}")
async def scan_barcode(request: Request, barcode: str):
    """Scan product by barcode."""
    uid=_require_user(request)
    if not uid:
        return JSONResponse({'error':'not_authenticated'}, status_code=401)
    user_profile = get_user_profile(uid)
    
    # Check cache first
    product = get_cached_product(barcode)
    
    # If not in cache, fetch from Open Food Facts
    if not product:
        product = fetch_product(barcode)
        if product:
            cache_product(barcode, product)
    
    if not product:
        return JSONResponse(
            status_code=404,
            content={"error": "Product not found"}
        )

    # USDA fallback if OFF is missing key nutrients
    if (product.get('calories') in (None, 0, '')) or (product.get('protein') in (None, 0, '')):
        try:
            extra = fallback_nutrition_for_name(product.get('name') or '')
            if extra:
                for k, v in extra.items():
                    if product.get(k) in (None, 0, '') and v not in (None, 0, ''):
                        product[k] = v
        except Exception:
            pass
    
    # Compute personalized score
    score, warnings, recommendation, breakdown = compute_personalized_score(
        product, user_profile
    )
    
    # Analyze additives
    additives_data = classify_additives(product.get('additives', ''))
    additives_summary = get_additive_summary(additives_data)
    harmful_chemicals = detect_harmful_chemicals(product)
    microplastics = detect_microplastics_risk(product)
    
    return {
        'product': product,
        'score': score,
        'warnings': warnings,
        'recommendation': recommendation,
        'breakdown': breakdown,
        'additives': additives_data,
        'additives_summary': additives_summary,
        'harmful_chemicals': harmful_chemicals,
        'microplastics': microplastics
    }

@app.get("/api/search")
async def search_food(q: str):
    """Search for products."""
    products = search_products(q)
    if not products:
        # Return sample products if search fails
        products = get_sample_products()
    return {'products': products[:10]}


@app.post("/api/photo-label")
async def photo_label(label: str = Form(...)):
    """Client-side AI (TFJS) sends a predicted food label.

We map that label into USDA FoodData Central search to get macros.
"""
    label = (label or "").strip()
    if not label:
        return JSONResponse(status_code=400, content={"error": "Missing label"})
    macros = None
    try:
        macros = fallback_nutrition_for_name(label)
    except Exception:
        macros = None
    if not macros:
        return {"label": label, "macros": None, "note": "No USDA match. Please log manually."}
    return {"label": label, "macros": macros}

@app.post("/api/log-food")
async def log_food(
    request: Request,
    product_name: str = Form(...),
    calories: float = Form(...),
    protein: float = Form(0),
    carbs: float = Form(0),
    fat: float = Form(0),
    sugar: float = Form(0),
    sodium: float = Form(0),
    fiber: float = Form(0),
    additives_count: int = Form(0),
    nova_group: int | None = Form(None),
    nutri_score: str = Form(''),
    score: int = Form(0),
    source: str = Form('manual')
):
    """Log a food entry."""
    uid=_require_user(request)
    if not uid:
        return JSONResponse({'error':'not_authenticated'}, status_code=401)
    
    log_data = {
        'user_id': uid,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'product_name': product_name,
        'calories': calories,
        'protein': protein,
        'carbs': carbs,
        'fat': fat,
        'sugar': sugar,
        'sodium': sodium,
        'fiber': fiber,
        'additives_count': additives_count,
        'nova_group': nova_group,
        'nutri_score': nutri_score,
        'score': score,
        'source': source,
    }
    
    log_id = save_food_log(log_data)
    
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/api/log-water")
async def log_water(request: Request, amount_ml: int = Form(...)):
    """Log water intake."""
    uid=_require_user(request)
    if not uid:
        return JSONResponse({'error':'not_authenticated'}, status_code=401)
    save_water_log(uid, datetime.now().strftime('%Y-%m-%d'), int(amount_ml))
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/api/chat")
async def chat(request: Request, message: str = Form(...)):
    """AI coach chat endpoint."""
    uid=_require_user(request)
    if not uid:
        return JSONResponse({'error':'not_authenticated'}, status_code=401)
    profile = get_user_profile(uid) or {}
    recent = get_food_logs(uid)
    reply = generate_coach_response(profile, recent, message)
    return {"reply": reply}


@app.post("/api/meal/analyze")
async def meal_analyze(request: Request, image: UploadFile = File(...)):
    """Photo meal scan.

    Practical hackathon behavior:
    - Try a local HF image classification pipeline if installed.
    - Map the predicted label to USDA name search.
    - Return suggested macros (per serving heuristic) + label.
    """
    uid=_require_user(request)
    if not uid:
        return JSONResponse({'error':'not_authenticated'}, status_code=401)
    
    content = await image.read()
    label = "unknown"
    confidence = 0.0
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(content)).convert("RGB")
        try:
            from transformers import pipeline
            clf = pipeline("image-classification", model=os.getenv("HF_FOOD_MODEL", "nateraw/food"))
            out = clf(img)
            if out:
                label = out[0].get("label", "unknown")
                confidence = float(out[0].get("score", 0.0) or 0.0)
        except Exception:
            # If transformers not available, keep unknown
            pass
    except Exception:
        pass

    macros = None
    if label != "unknown":
        try:
            macros = fallback_nutrition_for_name(label)
        except Exception:
            macros = None

    return {
        "label": label,
        "confidence": confidence,
        "macros": macros or {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "sugar": 0, "sodium": 0},
        "note": "Photo estimation is approximate. Confirm with label/manual edits."
    }

@app.get("/api/stats")
async def get_stats(request: Request):
    """Get user statistics."""
    uid=_require_user(request)
    if not uid:
        return JSONResponse({'error':'not_authenticated'}, status_code=401)
    user_profile = get_user_profile(uid)
    logs = get_food_logs(uid)
    
    if not user_profile:
        return {'error': 'No user profile found'}
    
    health_score = calculate_health_score(logs, user_profile)
    weekly_stats = get_weekly_stats(logs)
    
    return {
        'health_score': health_score,
        'weekly_stats': weekly_stats,
        'targets': {
            'calories': user_profile.get('calorie_target'),
            'protein': user_profile.get('protein_target'),
            'carbs': user_profile.get('carb_target'),
            'fat': user_profile.get('fat_target')
        }
    }

## NOTE: /api/chat is the single coach endpoint used by the UI.

@app.get("/api/sample-products")
async def get_samples():
    """Get sample products for demo."""
    return {'products': get_sample_products()}


@app.get("/menu", response_class=HTMLResponse)
async def menu_page(request: Request):
    """Restaurant menu scan (OCR)."""
    uid=_require_user(request)
    if not uid:
        return RedirectResponse('/login', status_code=303)
    user_profile = get_user_profile(uid)
    if not user_profile:
        return RedirectResponse(url="/get-started", status_code=303)
    return templates.TemplateResponse("menu.html", _tpl_ctx(request, show_nav=True, active_tab="scan", user=user_profile))


@app.post("/api/menu/ocr")
async def menu_ocr(request: Request, image: UploadFile = File(...)):
    """OCR a menu image and rank items for the user profile."""
    uid=_require_user(request)
    if not uid:
        return JSONResponse({'error':'not_authenticated'}, status_code=401)
    profile = get_user_profile(uid) or {}
    content = await image.read()
    items = ocr_menu_items(content)
    ranked = recommend_menu_items(items, profile)
    return {"items": items, "recommendations": ranked}


@app.get("/api/reports/weekly.pdf")
async def weekly_report_pdf(request: Request):
    """Download weekly PDF report (no GPT required)."""
    uid=_require_user(request)
    if not uid:
        return JSONResponse({"error":"not_authenticated"}, status_code=401)
    profile = get_user_profile(uid) or {}
    logs = get_food_logs(uid)
    pdf_bytes = build_weekly_pdf(profile, logs)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=nutrivision-weekly-report.pdf"},
    )


from services.llm import answer as llm_answer
from services.photo_scan import analyze_photo

@app.post("/api/v1/scan")
async def v1_scan(request: Request, barcode: str = Form(...)):
    """Trigger scan + cache; use query param barcode from JS."""
    uid=_require_user(request)
    if not uid:
        return JSONResponse({"error":"not_authenticated"}, status_code=401)
    product = fetch_product(barcode)
    if not product:
        return JSONResponse({"found": False}, status_code=404)
    cache_product(barcode, product)
    return {"found": True, "barcode": barcode}

@app.post("/api/v1/food-scanner")
async def v1_food_scanner(request: Request, file: UploadFile = File(...)):
    """Food photo scanner endpoint."""
    uid=_require_user(request)
    if not uid:
        return JSONResponse({"error":"not_authenticated"}, status_code=401)
    image_bytes = await file.read()
    res = analyze_photo(image_bytes)
    # map USDA -> macros (best effort)
    macros = {"calories": None, "protein": None, "carbs": None, "fat": None}
    if res.get("usda"):
        # current usda_api returns a dict already normalized
        u = res["usda"]
        macros["calories"] = u.get("calories")
        macros["protein"] = u.get("protein")
        macros["carbs"] = u.get("carbs")
        macros["fat"] = u.get("fat")
    return {"label": res["label"], "confidence": res["confidence"], **macros}

@app.post("/api/v1/coach")
async def v1_coach(request: Request, message: str = Form(...)):
    """V1 coach endpoint."""
    uid=_require_user(request)
    if not uid:
        return JSONResponse({"error":"not_authenticated"}, status_code=401)
    profile = get_user_profile(uid) or {}
    logs = get_food_logs(uid)[:20]
    prompt = f"""You are NutriVision, a careful nutrition coach.
User profile: {profile}
Recent logs (latest first): {logs}
User question: {message}

Rules:
- Be practical and concise.
- If user has diabetes/hypertension/etc, give condition-aware guidance.
- If you mention limits, give a safe conservative range, and say to consult clinician for medical advice.
Answer:"""
    reply = llm_answer(prompt)
    return {"reply": reply}

@app.post("/api/v1/meal-planner")
async def v1_meal_planner(request: Request):
    """Meal planner endpoint."""
    uid=_require_user(request)
    if not uid:
        return JSONResponse({"error":"not_authenticated"}, status_code=401)
    profile = get_user_profile(uid) or {}
    prompt = f"""Generate a 1-day meal plan as JSON with keys breakfast,lunch,dinner,snacks.
Use Nepal-friendly common foods when possible.
User profile: {profile}
Targets: calories={profile.get('calorie_target')} protein={profile.get('protein_target')} carbs={profile.get('carb_target')} fat={profile.get('fat_target')}
Constraints: respect conditions/allergies.
Return ONLY JSON."""
    out = llm_answer(prompt)
    try:
        plan = json.loads(out)
    except Exception:
        plan = {"breakfast": out}
    return {"plan": plan}

@app.post("/api/v1/workout-planner")
async def v1_workout_planner(request: Request):
    """Workout planner endpoint."""
    uid=_require_user(request)
    if not uid:
        return JSONResponse({"error":"not_authenticated"}, status_code=401)
    profile = get_user_profile(uid) or {}
    prompt = f"""Create a simple 3-day/week workout routine for the user's goal.
User profile: {profile}
Return as JSON with keys day1,day2,day3. Include warmup + main + cooldown.
Return ONLY JSON."""
    out = llm_answer(prompt)
    try:
        plan = json.loads(out)
    except Exception:
        plan = {"day1": out}
    return {"plan": plan}


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "NutriVision AI"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)  # Set reload=False for production; True for development with auto-reload on code changes.