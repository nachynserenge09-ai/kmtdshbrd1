import asyncio, hashlib, hmac, json, os, sqlite3, time, urllib.request
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, time as dtime
from pathlib import Path
from urllib.parse import parse_qsl

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo,
)
from aiogram.filters import CommandStart, Command

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "kmt.db"
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GAS_URL = os.getenv("GAS_URL", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
REFRESH_SECONDS = 30 * 60

BELLS = [
    {"n": 1, "start": "08:30", "end": "10:00"},
    {"n": 2, "start": "10:30", "end": "12:00"},
    {"n": 3, "start": "12:20", "end": "13:50"},
    {"n": 4, "start": "14:00", "end": "15:30"},
    {"n": 5, "start": "15:40", "end": "17:10"},
]

# --- преподаватели и их дисциплины (из твоего файла) ---
TEACHERS = {
    "Балыкина Елена Ивановна": ["Материаловедение", "Теплотехника", "Термическая обработка металлов и сплавов", "Типовые технологии производства", "Физическая химия", "Химические и физико-химические методы анализа"],
    "Бируля Татьяна Анатольевна": ["Информатика и ИКТ", "Психология делового общения", "Психология социально-правовой деятельности"],
    "Бородина Елена Николаевна": ["1С:Предприятие", "Информатика", "Информатика и ИКТ", "Информационные технологии в профессиональной деятельности", "Операционные системы и среды", "Основы теории информации", "Технические средства информатизации"],
    "Василевская Светлана Николаевна": ["Информатика и ИКТ"],
    "Васильева Валентина Сергеевна": ["Биология", "Основы безопасности жизнедеятельности"],
    "Вертышева Елена Анатольевна": ["Иностранный язык"],
    "Воробьева Светлана Николаевна": ["Основы электромонтажных работ", "Электрическое оборудование цехов по производству черных металлов", "Электронная техника", "Электрооборудование цехов ОМД", "Электротехника", "Электротехника и электроника"],
    "Гокова Ирина Геннадьевна": ["Естествознание", "Физика"],
    "Губарева Анна Васильевна": ["История", "Обществознание", "Юридическая психология"],
    "Давыдова Екатерина Викторовна": ["Физическая культура"],
    "Долбня Марина Сергеевна": ["Страховое дело", "Уголовное право", "Уголовный процесс"],
    "Ерёменко Александр Викторович": ["Организационно-управленческая деятельность", "Основы управления в правоохранительных органах"],
    "Журавлева Людмила Николаевна": ["Литература", "Русский язык"],
    "Зыльков Александр Захарович": ["Информатика", "Информатика и ИКТ", "Информационные технологии в профессиональной деятельности", "Оформление проектной документации"],
    "Зылькова Ирина Владимировна": ["Автоматизация технологических процессов", "Контроль соответствия и надежность устройств", "Метрология, стандартизация и сертификация", "Обеспечение надежности систем автоматизации", "Средства измерений", "Техническое обслуживание и эксплуатация"],
    "Исакова Оксана Владиславовна": ["Автоматизация", "Материаловедение", "Спецтехнология", "Химия"],
    "Карташова Анфиса Сергеевна": ["Делопроизводство и режим секретности", "Семейное право", "Трудовое право"],
    "Кипинган Наталья Сергеевна": ["Административное право", "Конституционное право", "Муниципальное право", "Основы экологического права"],
    "Коновалова Марина Геннадьевна": ["Механическое и подъемно-транспортное оборудование сталеплавильных цехов", "Технологическое оборудование сталеплавильных цехов", "Технология производства стали", "Управление технологическими процессами"],
    "Корнаушенко Константин  Владимирович": ["Физическая культура"],
    "Кравцова Ольга Александровна": ["Специальные измерения в металлургии", "Теория автоматического управления", "ТЭСАУ"],
    "Ксеневич Наталья Ивановна": ["Безопасность жизнедеятельности", "Охрана труда", "Промышленная безопасность и охрана труда", "Технология исследовательской деятельности", "Экология металлургического производства"],
    "Кузнецова Ирина Ивановна": ["Криминалистика", "Организация раскрытия и расследования преступлений"],
    "Лило Лиана Рашитовна": ["Иностранный язык"],
    "Лисота Наталия Алексеевна": ["Искусство (МХК)", "История", "Обществознание", "Обществознание (включая экономику и право)", "Основы философии", "Правовое обеспечение профессиональной деятельностим", "Правовое регулирование трудовых отношений", "Правовые основы профессиональной деятельности"],
    "Макаров Николай Борисович": ["Конституционное право"],
    "Малицкая Екатерина Владимировна": ["Гражданское право и гражданский процесс", "Криминология и предупреждение преступлений", "Семейное право", "Трудовое право", "Уголовный процесс"],
    "Манина Татьяна Владимировна": ["Специальная мехатроника"],
    "Миклина Лариса Владимировна": ["Математика"],
    "Москалец Ярослава Васильевна": ["Менеджмент", "Организация производственного процесса", "Основы экономики", "Экономика организации", "Экономика отрасли", "Экономическая теория"],
    "Норкина Влада Ивановна": ["Иностранный язык"],
    "Петров Денис Сергеевич": ["Гражданское право и гражданский процесс", "Начальная профессиональная подготовка", "Тактико-специальная подготовка"],
    "Пороль Варвара Викторовна": ["География", "Естествознание", "Химия", "Экологические основы природопользования"],
    "Романов Андрей Андреевич": ["Метрологическое обеспечение", "Основы проектирования цеха ОМД и его грузопотоки", "Основы технологии отрасли", "Теория обработки металлов давлением", "Теплотехника", "Технологические процессы ОМД"],
    "Серова Наталья Викторовна": ["Правила технической эксплуатации", "Станции и узлы", "Техническая эксплуатация и безопасность движения", "Технология перевозочного процесса"],
    "Соколов Сергей Валерьевич": ["Информационное обеспечение перевозочного процесса", "Информационные технологии в профессиональной деятельности", "Обработка отраслевой информации", "Основы компьютерного моделирования", "Основы разработки прикладных решений", "ОСУ на базе программируемых контроллеров", "Оформление проектной документации", "Разработка, внедрение и адаптация ПО", "Технология исследовательской деятельности"],
    "Соловьева Анна Владимировна": ["Гражданский процесс", "Гражданское право и гражданский процесс", "Иностранный язык", "Семейное право", "Трудовое право"],
    "Степанова Лидия Викторовна": ["Иностранный язык"],
    "Тростинецкая Елена Владимировна": ["Литература", "Родная литература", "Русский язык", "Русский язык и культура речи"],
    "Фомичева Ксения Валерьевна": ["Организация работы органов социального обеспечения", "Право социального обеспечения"],
    "Фролова Юлия Эдуардовна": ["Иностранный язык"],
    "Хамина Оксана Евгеньевна": ["Документационное обеспечение управления", "Инженерная графика", "Техническая механика"],
    "Шмыгова Ольга Валерьевна": ["Физическая культура"],
    "Яковлева Виктория Витальевна": ["Гражданское право", "Теория государства и права"],
    "Ачинович Светлана Алексеевна": [],
    "Пальк Эдуард Александрович": [],
    "Пегасина Ксения Андреевна": ["Математика"],
    "Порозова Софья Викторовна": [],
}

WEEKDAY_ORDER = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
SCHEDULE = {"updated": None, "dates": [], "groups": [], "data": {}}

def parse_schedule(raw):
    base_iso, base_idx = None, None
    for idx, sheet in enumerate(raw):
        d = str(sheet.get("дата") or "").strip()
        if not d: continue
        try:
            base_iso = datetime.strptime(d, "%d.%m.%Y")
            base_idx = idx
            break
        except ValueError: continue

    dates, data, groups = [], {}, set()

    for idx, sheet in enumerate(raw):
        name = str(sheet.get("лист") or "").strip()
        d = str(sheet.get("дата") or "").strip()

        if d:
            try: dt = datetime.strptime(d, "%d.%m.%Y")
            except ValueError: continue
        elif base_iso is not None and name in WEEKDAY_ORDER:
            base_name = str(raw[base_idx].get("лист") or "Понедельник").strip()
            if base_name not in WEEKDAY_ORDER: base_name = "Понедельник"
            offset = WEEKDAY_ORDER.index(name) - WEEKDAY_ORDER.index(base_name)
            if offset < 0: offset += 7
            dt = base_iso + timedelta(days=offset)
        else: continue

        iso = dt.strftime("%Y-%m-%d")
        by_group = {}
        for row in sheet.get("данные", []):
            group = str(row.get("Группа") or "").strip()
            if not group: continue
            lessons = []
            for i in range(1, 6):
                title = str(row.get(f"{i} пара") or "").strip()
                room = str(row.get(f"ауд{i}") or "").strip()
                if not title or title.lower().startswith("нет занят"): continue
                if room.lower() == "нет": room = ""
                lessons.append({"num": i, "title": title, "room": room})
            by_group[group] = lessons
            groups.add(group)

        data[iso] = by_group
        dates.append({"date": iso, "iso": iso, "weekday": name, "display": dt.strftime("%d.%m")})

    dates.sort(key=lambda x: x["iso"])
    seen, uniq = set(), []
    for d in dates:
        if d["date"] in seen: continue
        seen.add(d["date"])
        uniq.append(d)

    return {"dates": uniq, "data": data, "groups": sorted(groups)}

def fetch_schedule():
    req = urllib.request.Request(GAS_URL, headers={"User-Agent": "kmt-miniapp"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = json.loads(r.read().decode("utf-8"))
    SCHEDULE.update(parse_schedule(raw))
    SCHEDULE["updated"] = int(time.time())

async def refresher():
    while True:
        try:
            if GAS_URL: await asyncio.to_thread(fetch_schedule)
            else: print("GAS_URL не задан: расписание не загружается")
        except Exception as e: print("Не удалось обновить расписание:", e)
        await asyncio.sleep(REFRESH_SECONDS if SCHEDULE["dates"] else 60)

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.executescript("CREATE TABLE IF NOT EXISTS students(telegram_id INTEGER PRIMARY KEY, group_name TEXT);")
    con.commit(); con.close()

init_db()

BOT = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
DP = Dispatcher() if BOT else None

def student_by_tg(tg_id: int):
    con = db()
    s = con.execute("SELECT * FROM students WHERE telegram_id=?", (tg_id,)).fetchone()
    con.close()
    return s

def save_group(tg_id: int, group: str):
    con = db()
    con.execute("INSERT OR REPLACE INTO students VALUES(?,?)", (tg_id, group))
    con.commit(); con.close()

def schedule_for_group(group: str):
    return [{**d, "lessons": SCHEDULE["data"].get(d["date"], {}).get(group, [])} for d in SCHEDULE["dates"]]

def find_teachers_by_subject(subject: str):
    s = subject.strip().lower()
    res = []
    for name, subs in TEACHERS.items():
        for sub in subs:
            if s in sub.lower():
                res.append({"name": name, "subjects": subs})
                break
    return res

def find_subjects_by_teacher(name: str):
    n = name.strip().lower()
    for tname, subs in TEACHERS.items():
        if n in tname.lower(): return {"name": tname, "subjects": subs}
    return None

def main_kb():
    rows = [
        [InlineKeyboardButton(text="📚 Расписание уроков", callback_data="sch:days")],
        [InlineKeyboardButton(text="🔔 Расписание звонков", callback_data="bells")],
        [InlineKeyboardButton(text="👨‍🏫 Преподаватели", callback_data="teachers")],
    ]
    if WEBAPP_URL: rows.append([InlineKeyboardButton(text="🌐 Открыть приложение", web_app=WebAppInfo(url=WEBAPP_URL))])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")]])

def groups_kb():
    gs = SCHEDULE["groups"]
    rows, row = [], []
    for g in gs:
        row.append(InlineKeyboardButton(text=g, callback_data=f"reg:{g}"))
        if len(row) == 3: rows.append(row); row = []
    if row: rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def days_kb(group: str):
    ds = schedule_for_group(group)
    rows, row = [], []
    for d in ds:
        label = f"{d['weekday'][:2]} {d.get('display', d['date'][5:])}"
        row.append(InlineKeyboardButton(text=label, callback_data=f"day:{d['date']}"))
        if len(row) == 3: rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def rooms_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Найти преподавателя по фамилии", callback_data="search_teacher")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
    ])

@DP.message(CommandStart())
async def cmd_start(m: Message):
    s = student_by_tg(m.from_user.id)
    if not s:
        if not SCHEDULE["groups"]: return await m.answer("Расписание ещё загружается. Попробуй через минуту.")
        return await m.answer("Привет! Выбери свою группу:", reply_markup=groups_kb())
    await m.answer(f"Группа {s['group_name']}. Что посмотрим?", reply_markup=main_kb())

@DP.message(Command("today"))
async def cmd_today(m: Message):
    s = student_by_tg(m.from_user.id)
    if not s: return await m.answer("Сначала /start и выбери группу.")
    today = datetime.now().strftime("%Y-%m-%d")
    day = next((d for d in schedule_for_group(s["group_name"]) if d["date"] == today), None)
    if not day: return await m.answer("На сегодня пары не найдены.")
    await send_day(m, day)

@DP.message(Command("teachers"))
async def cmd_teachers(m: Message):
    await m.answer("Нажми кнопку ниже:", reply_markup=rooms_kb())

@DP.callback_query(F.data == "menu")
async def cb_menu(c: CallbackQuery):
    await c.message.edit_text("Главное меню:", reply_markup=main_kb())
    await c.answer()

@DP.callback_query(F.data.startswith("reg:"))
async def cb_reg(c: CallbackQuery):
    group = c.data.split(":", 1)[1]
    if group not in SCHEDULE["groups"]: return await c.answer("Такой группы нет", show_alert=True)
    save_group(c.from_user.id, group)
    await c.message.edit_text(f"Готово! Ты в группе {group}.", reply_markup=main_kb())
    await c.answer()

@DP.callback_query(F.data == "bells")
async def cb_bells(c: CallbackQuery):
    text = "🔔 Расписание звонков:\n\n" + "\n".join(f"{b['n']} пара: {b['start']}–{b['end']}" for b in BELLS)
    await c.message.edit_text(text, reply_markup=back_kb())
    await c.answer()

@DP.callback_query(F.data == "teachers")
async def cb_teachers(c: CallbackQuery):
    await c.message.edit_text("👨‍🏫 Преподаватели\n\nНапиши фамилию — покажу дисциплины.", reply_markup=rooms_kb())
    await c.answer()

@DP.callback_query(F.data == "search_teacher")
async def cb_search_teacher(c: CallbackQuery):
    await c.message.edit_text("Напиши фамилию преподавателя (например: Тростинецкая):")
    await c.answer()

@DP.message(F.text & ~F.text.startswith("/"))
async def on_text(m: Message):
    q = m.text.strip()
    t = find_subjects_by_teacher(q)
    if t:
        subs = t["subjects"]
        text = f"👨‍🏫 {t['name']}\n\n" + ("Дисциплины:\n" + "\n".join(f"• {s}" for s in subs) if subs else "Дисциплины не указаны.")
        return await m.answer(text, reply_markup=back_kb())
    
    subs_list = find_teachers_by_subject(q)
    if subs_list:
        lines = [f"📚 По запросу «{q}» найдено:"]
        for item in subs_list[:15]: lines.append(f"• {item['name']}")
        if len(subs_list) > 15: lines.append(f"…и ещё {len(subs_list)-15}")
        return await m.answer("\n".join(lines), reply_markup=back_kb())
    
    await m.answer("Ничего не нашёл. Проверь написание.", reply_markup=back_kb())

@DP.callback_query(F.data == "sch:days")
async def cb_sch_days(c: CallbackQuery):
    s = student_by_tg(c.from_user.id)
    if not s: return await c.answer("Сначала /start", show_alert=True)
    if not SCHEDULE["dates"]: return await c.answer("Расписание ещё не загружено", show_alert=True)
    await c.message.edit_text("Выбери день:", reply_markup=days_kb(s["group_name"]))
    await c.answer()

@DP.callback_query(F.data.startswith("day:"))
async def cb_day(c: CallbackQuery):
    date = c.data.split(":", 1)[1]
    s = student_by_tg(c.from_user.id)
    if not s: return await c.answer("Сначала /start", show_alert=True)
    day = next((d for d in schedule_for_group(s["group_name"]) if d["date"] == date), None)
    if not day: return await c.answer("Нет данных", show_alert=True)
    await send_day(c.message, day)
    await c.answer()

async def send_day(target, day):
    s = student_by_tg(target.chat.id if hasattr(target, "chat") else target.from_user.id)
    group = s["group_name"] if s else ""
    bells = {b["n"]: b for b in BELLS}
    if not day["lessons"]:
        text = f"📚 {day['weekday']} {day['date']} ({group}):\n\nПар нет."
    else:
        lines = []
        now = datetime.now(); today = now.strftime("%Y-%m-%d")
        for l in day["lessons"]:
            room = "дистанционно" if l["room"] == "ДО" else (f"каб. {l['room']}" if l["room"] else "")
            b = bells.get(l["num"]); t = f" {b['start']}–{b['end']}" if b else ""
            mark = ""
            if day["date"] == today and b:
                start = datetime.combine(now.date(), dtime.fromisoformat(b["start"]))
                end = datetime.combine(now.date(), dtime.fromisoformat(b["end"]))
                if start <= now <= end: mark = "  🟢 сейчас"
                elif now < start: mark = "  ⏳ далее"
            lines.append(f"{l['num']}. {l['title']} — {room}{t}{mark}")
        text = f"📚 {day['weekday']} {day['date']} ({group}):\n\n" + "\n".join(lines)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Дни", callback_data="sch:days")], [InlineKeyboardButton(text="🏠 В меню", callback_data="menu")]])
    if hasattr(target, "edit_text"): await target.edit_text(text, reply_markup=kb)
    else: await target.answer(text, reply_markup=kb)

@asynccontextmanager
async def lifespan(app):
    tasks = [asyncio.create_task(refresher())]
    if BOT and DP: tasks.append(asyncio.create_task(DP.start_polling(BOT)))
    yield
    for t in tasks: t.cancel()

app = FastAPI(lifespan=lifespan)

def get_user(init_data: str) -> dict:
    if not BOT_TOKEN: return {"id": 1, "first_name": "Тест"}
    try:
        data = dict(parse_qsl(init_data, strict_parsing=True))
        received_hash = data.pop("hash")
        check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc, received_hash): raise ValueError("bad hash")
        if time.time() - int(data["auth_date"]) > 86400: raise ValueError("expired")
        return json.loads(data["user"])
    except Exception: raise HTTPException(401, "Неверные данные Telegram")

@app.get("/api/me")
def me(x_init_data: str = Header(default="")):
    user = get_user(x_init_data)
    con = db()
    s = con.execute("SELECT * FROM students WHERE telegram_id=?", (user["id"],)).fetchone()
    con.close()
    return {"registered": bool(s), "group": s["group_name"] if s else None, "groups": SCHEDULE["groups"]}

class Reg(BaseModel): group: str

@app.post("/api/register")
def register(r: Reg, x_init_data: str = Header(default="")):
    user = get_user(x_init_data)
    if r.group not in SCHEDULE["groups"]: raise HTTPException(400, "Такой группы нет в расписании")
    save_group(user["id"], r.group)
    return {"ok": True}

@app.get("/api/schedule")
def api_schedule(x_init_data: str = Header(default="")):
    user = get_user(x_init_data)
    con = db()
    s = con.execute("SELECT group_name FROM students WHERE telegram_id=?", (user["id"],)).fetchone()
    con.close()
    if not s: raise HTTPException(404, "Сначала зарегистрируйтесь")
    dates = [{**d, "lessons": SCHEDULE["data"].get(d["date"], {}).get(s["group_name"], [])} for d in SCHEDULE["dates"]]
    return {"dates": dates, "bells": BELLS, "updated": SCHEDULE["updated"], "group": s["group_name"]}

@app.get("/api/teachers")
def api_teachers(q: str = Query(default="", max_length=64)):
    if not q: return {"items": [{"name": n, "subjects": s} for n, s in sorted(TEACHERS.items())]}
    res = [{"name": name, "subjects": subs} for name, subs in TEACHERS.items() if q.lower() in name.lower()]
    return {"items": res}

@app.get("/api/subjects")
def api_subjects(q: str = Query(default="", max_length=64)):
    res = []
    for name, subs in TEACHERS.items():
        for sub in subs:
            if q.lower() in sub.lower(): res.append({"subject": sub, "teacher": name})
    return {"items": res}

@app.get("/", response_class=HTMLResponse)
def index(): return (BASE_DIR / "index.html").read_text(encoding="utf-8")