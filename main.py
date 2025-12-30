import flet as ft
import requests
import json
import smtplib
import threading
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os
import sys

# --- AYARLAR ---
FIREBASE_WEB_API_KEY = "AIzaSyC4QY3fwMNvgSvFGtl63KBtRzzdWZK7tt4" 
DATABASE_URL = "https://galataservis-4ae05-default-rtdb.europe-west1.firebasedatabase.app/"
COLOR_PRIMARY = "#960000"
COLOR_BG = "#1a1a1a"
COLOR_CARD = "#2b2b2b"
COLOR_TEXT_HINT = "#aaaaaa"
COLOR_WARNING = "#F44336"
COLOR_SUCCESS = "#4CAF50"

# --- MAİL AYARLARI ---
SMTP_EMAIL = "suleymanerkan@galatajenerator.com.tr" 
SMTP_PASSWORD = "zgod yvli kgos piel"  
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
ADMIN_MAIL = "suleymanerkan@galatajenerator.com.tr" 

# --- OTURUM BİLGİSİ ---
CURRENT_USER = {
    "email": None,
    "role": None,
    "name": None,
    "plate": None,
    "token": None
}

def main(page: ft.Page):
    page.title = "Galata Mobil"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = COLOR_BG
    page.assets_dir = "assets"
    page.window_icon = "galata_logo.png"

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)
    
    page.on_view_pop = view_pop

    # --- YARDIMCI FONKSİYONLAR ---
    
    def safe_open_file(path):
        if sys.platform == "win32":
            try: os.startfile(path)
            except: pass
        else:
            print(f"Mobil ortamda dosya yolu: {path}")

    def normalize_list(data):
        if isinstance(data, list): return [x for x in data if x is not None]
        elif isinstance(data, dict):
            try: return [data[k] for k in sorted(data.keys(), key=lambda x: int(x) if str(x).isdigit() else x)]
            except: return list(data.values())
        return []

    def tr_upper(text):
        if not text: return ""
        text = str(text).replace("i", "İ").replace("ı", "I").replace("ğ", "Ğ").replace("ü", "Ü").replace("ş", "Ş").replace("Ö", "ö").replace("ç", "Ç")
        return text.upper().strip()

    def normalize_search_text(text):
        if not text: return ""
        text = str(text)
        replacements = {"İ": "i", "I": "i", "ı": "i", "Ş": "s", "ş": "s", "Ğ": "g", "ğ": "g", "Ü": "u", "ü": "u", "Ö": "o", "ö": "o", "Ç": "c", "ç": "c"}
        text = "".join([replacements.get(c, c) for c in text])
        return text.lower()

    def date_formatter(e):
        val = e.control.value
        if not val: return
        digits = "".join([c for c in val if c.isdigit()])
        formatted = digits
        if len(digits) >= 3: formatted = digits[:2] + "." + digits[2:]
        if len(digits) >= 5: formatted = formatted[:5] + "." + formatted[5:]
        if len(formatted) > 10: formatted = formatted[:10]
        if e.control.value != formatted:
            e.control.value = formatted; e.control.update()

    def currency_formatter(e):
        val = str(e.control.value).strip()
        if not val: return
        clean_val = val.replace(" TL", "").replace("TL", "").strip()
        try:
            if "," in clean_val and "." in clean_val: clean_val = clean_val.replace(".", "").replace(",", ".")
            elif "," in clean_val: clean_val = clean_val.replace(",", ".")
            float_val = float(clean_val)
            formatted = "{:,.2f}".format(float_val)
            formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
            final_text = f"{formatted} TL"
            if e.control.value != final_text:
                e.control.value = final_text
                e.control.update()
        except: pass

    def detail_row(label, value, icon_name=None, color="white", is_warning=False):
        text_color = COLOR_WARNING if is_warning else color
        val_str = str(value).strip()
        if not val_str or val_str == "None": val_str = "-"
        return ft.Container(content=ft.Row([
            ft.Icon(name=icon_name, size=18, color=COLOR_PRIMARY) if icon_name else ft.Container(width=18),
            ft.Text(f"{label}: ", weight="bold", color="white", size=13, width=110),
            ft.Text(val_str, color=text_color, size=13, selectable=True, expand=True, weight="bold" if is_warning else "normal")
        ], alignment=ft.MainAxisAlignment.START), padding=2)

    def show_snack(text, is_error=False):
        try: page.close_snack_bar()
        except: pass
        snack = ft.SnackBar(content=ft.Text(text, color="white", weight="bold"), bgcolor="#D32F2F" if is_error else "#388E3C")
        page.open(snack)

    def confirm_action(title, message, action_callback):
        def on_yes(e): page.close(dlg); action_callback()
        dlg = ft.AlertDialog(title=ft.Text(title), content=ft.Text(message), actions=[ft.TextButton("İPTAL", on_click=lambda e: page.close(dlg)), ft.ElevatedButton("EVET, SİL", on_click=on_yes, bgcolor="red", color="white")])
        page.open(dlg)

    # --- VERİTABANI İŞLEMLERİ ---
    def get_data(node):
        try:
            url = f"{DATABASE_URL}{node}.json"
            if CURRENT_USER["token"]:
                url += f"?auth={CURRENT_USER['token']}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200 and res.text != "null":
                return res.json()
            elif res.status_code == 401:
                return []
            return []
        except: return []

    def update_data(path, data):
        try:
            url = f"{DATABASE_URL}{path}.json"
            if CURRENT_USER["token"]:
                url += f"?auth={CURRENT_USER['token']}"
            res = requests.put(url, json=data, timeout=10)
            return res.status_code == 200
        except: return False

    def update_firebase_user_plate(email, plaka):
        if not email: return
        users = get_data("kullanicilar")
        if users:
            for k, v in users.items():
                if v.get('email') == email:
                    url = f"{DATABASE_URL}kullanicilar/{k}.json"
                    if CURRENT_USER["token"]: url += f"?auth={CURRENT_USER['token']}"
                    requests.patch(url, json={'plaka': plaka, 'yetkili_plaka': plaka})
                    return

    # --- GİRİŞ VE MAİL ---
    def login_with_firebase(email, password):
        if "BURAYA" in FIREBASE_WEB_API_KEY:
            return None
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        try:
            r = requests.post(url, json=payload)
            if r.status_code == 200:
                return r.json()
            else:
                return None
        except Exception as e:
            return None

    def send_generic_mail(to_list, subject, body):
        try:
            valid_to = [email for email in to_list if email and "@" in email]
            if not valid_to: return False
            msg = MIMEText(body)
            msg['Subject'] = subject; msg['From'] = SMTP_EMAIL; msg['To'] = ", ".join(valid_to)
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls(); server.login(SMTP_EMAIL, SMTP_PASSWORD); server.sendmail(SMTP_EMAIL, valid_to, msg.as_string())
            return True
        except: return False

    # --- AKILLI HATIRLATMA ---
    def check_daily_reminders():
        if not CURRENT_USER["token"]: return
        today = datetime.now()
        today_str = today.strftime("%d.%m.%Y")
        logs = page.client_storage.get("reminder_logs")
        if not logs or logs.get("last_run") != today_str:
            logs = {"last_run": today_str, "sent_keys": []}
            
        alerts = []; mail_queue = []; log_changed = False
        araclar = normalize_list(get_data("araclar"))
        personel_list = normalize_list(get_data("personel"))
        p_mails = {}
        for p in personel_list:
            fname = f"{p.get('ad','')} {p.get('soyad','')}".strip().upper()
            if p.get('email'): p_mails[fname] = p.get('email')

        if araclar:
            for v in araclar:
                if not v: continue
                plaka = v.get('plaka', 'Bilinmeyen'); zimmetli = str(v.get('zimmetli_personel', '')).strip().upper()
                driver_mail = p_mails.get(zimmetli); to_send = [ADMIN_MAIL]
                if driver_mail: to_send.append(driver_mail)
                checks = [('muayene_tarihi', 'Muayene'), ('sigorta_tarihi', 'Sigorta'), ('kasko_tarihi', 'Kasko'), ('egzoz_tarihi', 'Egzoz')]
                for key, label in checks:
                    d_str = v.get(key)
                    if d_str and len(d_str) >= 10:
                        try:
                            t_date = datetime.strptime(d_str, "%d.%m.%Y"); diff = (t_date - today).days
                            unique_key = f"{plaka}_{label}_{today_str}"
                            if unique_key in logs["sent_keys"]: continue
                            if 0 <= diff <= 5:
                                alerts.append(f"⚠️ {plaka} - {label}: {diff} gün kaldı!")
                                subj = f"UYARI: {plaka} - {label} Son {diff} Gün"
                                body = f"Merhaba,\n\n{plaka} plakalı aracın {label} tarihi yaklaştı ({d_str}).\nKalan: {diff} Gün.\nKullanıcı: {zimmetli}"
                                mail_queue.append((to_send, subj, body)); logs["sent_keys"].append(unique_key); log_changed = True
                        except: pass
                randevular = normalize_list(v.get('randevular', []))
                check_dates = [today.strftime("%d.%m.%Y"), (today + timedelta(days=1)).strftime("%d.%m.%Y")]
                for r in randevular:
                    r_date = r.get('tarih')
                    if r_date in check_dates and r.get('durum') != 'Tamamlandı':
                        unique_key = f"{plaka}_Randevu_{r_date}_{today_str}"
                        if unique_key in logs["sent_keys"]: continue
                        alerts.append(f"📅 RANDEVU: {plaka} ({r_date})")
                        subj = f"HATIRLATMA: {plaka} Randevusu Var"
                        body = f"Merhaba,\n\n{plaka} aracı için randevu görünüyor ({r_date}).\nİşlem: {r.get('aciklama')}\nKullanıcı: {zimmetli}"
                        mail_queue.append((to_send, subj, body)); logs["sent_keys"].append(unique_key); log_changed = True

        if alerts:
            lv = ft.ListView(expand=True, spacing=10, padding=10)
            for a in alerts:
                lv.controls.append(ft.Container(content=ft.Row([ft.Icon(name="warning", color="orange"), ft.Text(a, color="white", size=12)]), bgcolor="#333", padding=10, border_radius=5))
            def close_dlg(e): page.close(dlg_rem)
            dlg_rem = ft.AlertDialog(title=ft.Text("GÜNLÜK HATIRLATMALAR"), content=ft.Container(lv, height=300), actions=[ft.TextButton("TAMAM", on_click=close_dlg)])
            page.open(dlg_rem)
            if mail_queue:
                def send_all_mails():
                    for emails, subj, txt in mail_queue: send_generic_mail(emails, subj, txt)
                threading.Thread(target=send_all_mails, daemon=True).start()
        if log_changed: page.client_storage.set("reminder_logs", logs)

    # --- 1. KİŞİSEL GÖREVLERİM ---
    def create_my_tasks_view():
        gorevler = normalize_list(get_data("saha_gorevleri"))
        my_tasks_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, expand=True)
        show_completed = [False]

        def render_tasks():
            my_tasks_list.controls.clear()
            user_name = CURRENT_USER['name']
            filtered_tasks = []
            for i, t in enumerate(gorevler):
                if not t: continue
                p_name = str(t.get('personel', '')).strip()
                if normalize_search_text(p_name) == normalize_search_text(user_name):
                    filtered_tasks.append((i, t))
            
            if not filtered_tasks:
                my_tasks_list.controls.append(ft.Text("Size atanmış görev bulunamadı.", color="grey", text_align="center"))
                page.update()
                return

            my_tasks_list.controls.append(ft.Text("TAMAMLANANLAR" if show_completed[0] else "BEKLEYEN GÖREVLER", 
                                                  color="green" if show_completed[0] else "orange", weight="bold"))
            
            for idx, t in filtered_tasks:
                is_done = t.get('tamamlandi', False)
                if show_completed[0] != is_done: continue

                icon = "check_circle" if is_done else "pending_actions"
                color = "green" if is_done else "orange"
                
                def toggle_task(e, ix=idx):
                    gorevler[ix]['tamamlandi'] = not gorevler[ix]['tamamlandi']
                    if update_data(f"saha_gorevleri/{ix}/tamamlandi", gorevler[ix]['tamamlandi']):
                        show_snack("Durum Güncellendi", False)
                        render_tasks()

                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(name=icon, color=color),
                                ft.Text(f"{t.get('kod')} - {t.get('ad')}", weight="bold", expand=True),
                                ft.Text(t.get('tarih'), size=12, color="grey")
                            ]),
                            ft.Text(f"Müşteri: {t.get('musteri')}", size=12, italic=True),
                            ft.Divider(height=5),
                            ft.Text(t.get('aciklama'), size=14),
                            ft.Row([
                                ft.ElevatedButton(
                                    "Tamamlandı Olarak İşaretle" if not is_done else "Geri Al",
                                    icon="check" if not is_done else "undo",
                                    bgcolor="green" if not is_done else "grey",
                                    color="white",
                                    height=30,
                                    on_click=lambda e, x=idx: toggle_task(e, x)
                                )
                            ], alignment=ft.MainAxisAlignment.END)
                        ]),
                        padding=10
                    ),
                    color=COLOR_CARD
                )
                my_tasks_list.controls.append(card)
            page.update()

        def toggle_view(e):
            show_completed[0] = not show_completed[0]
            btn_toggle.text = "BEKLEYENLERİ GÖSTER" if show_completed[0] else "TAMAMLANANLARI GÖSTER"
            btn_toggle.icon = "list" if show_completed[0] else "history"
            render_tasks()

        btn_toggle = ft.ElevatedButton("TAMAMLANANLARI GÖSTER", icon="history", on_click=toggle_view, bgcolor="#444", color="white")
        render_tasks()
        return ft.Column([ft.Container(content=btn_toggle, padding=10, alignment=ft.alignment.center), my_tasks_list], expand=True)

    # --- İŞ TAKİP ---
    def create_is_takip_view():
        raw_data = normalize_list(get_data("musteriler")); pending_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=5, expand=True); show_completed = [False]
        def render_tasks():
            pending_list.controls.clear()
            if not raw_data: pending_list.controls.append(ft.Text("Veri yok.", color="grey")); return
            pending_list.controls.append(ft.Text("TAMAMLANAN İŞLER" if show_completed[0] else "BEKLEYEN İŞLER", weight="bold", size=16, color="green" if show_completed[0] else "white", text_align="center")); pending_list.controls.append(ft.Divider())
            for c_idx, cust in enumerate(raw_data):
                if not cust: continue
                for a_idx, alan in enumerate(normalize_list(cust.get('alanlar', []))):
                    if not alan: continue
                    for t_idx, task in enumerate(normalize_list(alan.get('yapilacaklar', []))):
                        if not task: continue
                        is_done = task.get('done', False)
                        if show_completed[0] != is_done: continue
                        def delete_task_click(c, a, t):
                            def action():
                                tasks = normalize_list(raw_data[c]['alanlar'][a]['yapilacaklar']); del tasks[t]
                                if update_data(f"musteriler/{c}/alanlar/{a}/yapilacaklar", tasks): show_snack("Silindi", False); raw_data[c]['alanlar'][a]['yapilacaklar'] = tasks; render_tasks()
                            confirm_action("İş Sil", "Silinsin mi?", action)
                        def edit_task_click(c, a, t):
                            tasks = normalize_list(raw_data[c]['alanlar'][a]['yapilacaklar']); task_data = tasks[t]
                            txt_edit = ft.TextField(label="Görev Düzenle", value=task_data.get('text'), multiline=True)
                            def save_edit(e):
                                task_data['text'] = txt_edit.value; tasks[t] = task_data
                                if update_data(f"musteriler/{c}/alanlar/{a}/yapilacaklar", tasks): show_snack("Güncellendi", False); page.close(dlg_edit); raw_data[c]['alanlar'][a]['yapilacaklar'] = tasks; render_tasks()
                            dlg_edit = ft.AlertDialog(title=ft.Text("Görevi Düzenle"), content=txt_edit, actions=[ft.ElevatedButton("KAYDET", on_click=save_edit)]); page.open(dlg_edit)
                        lead = ft.Icon(name="done", color="green") if is_done else ft.Checkbox(value=False, on_change=lambda e, c=c_idx, a=a_idx, t=t_idx: complete_task(c, a, t))
                        btns = ft.Row([ft.IconButton(icon="edit", icon_color="blue", on_click=lambda e, c=c_idx, a=a_idx, t=t_idx: edit_task_click(c, a, t)), ft.IconButton(icon="delete", icon_color="red", on_click=lambda e, c=c_idx, a=a_idx, t=t_idx: delete_task_click(c, a, t))], spacing=0, width=100)
                        pending_list.controls.append(ft.Card(content=ft.ListTile(leading=lead, title=ft.Text(task.get('text', ''), weight="bold"), subtitle=ft.Text(f"{cust.get('ad')} - {alan.get('adi')}", size=12), trailing=btns), color="#222"))
            page.update()
        def toggle_view(e): show_completed[0] = not show_completed[0]; btn_toggle.text = "BEKLEYENLER" if show_completed[0] else "TAMAMLANAN İŞLER"; btn_toggle.icon = "list" if show_completed[0] else "done_all"; render_tasks()
        def complete_task(c, a, t):
            tasks = normalize_list(raw_data[c]['alanlar'][a]['yapilacaklar']); tasks[t]['done'] = True; tasks[t]['completed_by'] = CURRENT_USER['name']; tasks[t]['completed_date'] = datetime.now().strftime("%d.%m.%Y %H:%M")
            if update_data(f"musteriler/{c}/alanlar/{a}/yapilacaklar", tasks): show_snack("Tamamlandı", False); raw_data[c]['alanlar'][a]['yapilacaklar'] = tasks; render_tasks()
        def add_task_dialog(e):
            search = ft.TextField(label="Müşteri/Saha Ara", autofocus=True, prefix_icon="search"); res_col = ft.Column(scroll=ft.ScrollMode.AUTO, height=150); sel = {"c": None, "a": None}
            def pick(c, a, n): sel['c'] = c; sel['a'] = a; search.value = n; search.disabled = True; res_col.controls.clear(); page.update()
            def do_search(e):
                val = normalize_search_text(search.value); res_col.controls.clear(); cnt = 0
                if len(val) < 2: page.update(); return
                for ci, c in enumerate(raw_data):
                    if cnt >= 3: break
                    if not c: continue
                    c_match = val in normalize_search_text(c.get('ad', ''))
                    for ai, al in enumerate(normalize_list(c.get('alanlar', []))):
                        if cnt >= 3: break
                        if not al: continue
                        if c_match or val in normalize_search_text(al.get('adi', '')) or val in normalize_search_text(str(al.get('kod', ''))):
                            res_col.controls.append(ft.ListTile(title=ft.Text(f"{al.get('adi')} ({c.get('ad')})"), on_click=lambda e, x=ci, y=ai, n=f"{al.get('adi')} ({c.get('ad')})": pick(x, y, n))); cnt += 1
                page.update()
            search.on_change = do_search
            txt = ft.TextField(label="İş / Görev", multiline=True, min_lines=3); 
            def save(e):
                if sel['c'] is None or not txt.value: return
                c, a = sel['c'], sel['a']; t_list = normalize_list(raw_data[c]['alanlar'][a].get('yapilacaklar', []))
                t_list.append({"text": txt.value, "done": False, "date": datetime.now().strftime("%d.%m.%Y"), "added_by": CURRENT_USER['name']})
                if update_data(f"musteriler/{c}/alanlar/{a}/yapilacaklar", t_list): show_snack("Eklendi", False); page.close(dlg); raw_data[c]['alanlar'][a]['yapilacaklar'] = t_list; render_tasks()
            dlg = ft.AlertDialog(title=ft.Text("Yeni İş"), content=ft.Column([search, res_col, txt], width=300, height=450), actions=[ft.ElevatedButton("KAYDET", on_click=save)]); page.open(dlg)
        render_tasks()
        btn_add = ft.ElevatedButton("YENİ İŞ", icon="add", bgcolor="#F57C00", color="white", expand=True, on_click=add_task_dialog)
        btn_toggle = ft.ElevatedButton("TAMAMLANAN İŞLER", icon="done_all", bgcolor="#388E3C", color="white", expand=True, on_click=toggle_view)
        return ft.Column([ft.Container(content=ft.Row([btn_add, btn_toggle]), padding=10), pending_list], expand=True)

    # --- ARACIM ---
    def create_my_vehicle_view():
        plaka = str(CURRENT_USER.get('plate', '')).strip()
        if not plaka or plaka == "None": return ft.Container(content=ft.Text("Araç ataması yapılmamış.", color="red"), alignment=ft.alignment.center)
        araclar = normalize_list(get_data("araclar")); target_veh = None; target_idx = -1
        clean_target = normalize_search_text(plaka)
        for i, v in enumerate(araclar):
            if v and normalize_search_text(v.get('plaka','')) == clean_target: target_veh = v; target_idx = i; break
        if not target_veh: return ft.Container(content=ft.Text("Araç veritabanında bulunamadı.", color="red"), alignment=ft.alignment.center)
        km_ref = ft.Ref[ft.Text]()
        def read_only_row(label, val, ref=None):
            return ft.Container(content=ft.Row([ft.Text(f"{label}:", weight="bold", width=100, color="grey"), ft.Text(str(val), weight="bold", size=16, color="white", ref=ref)]), padding=5, bgcolor="#222", border_radius=5)
        def save_date_change(e, field_key):
            new_val = e.control.value
            if update_data(f"araclar/{target_idx}/{field_key}", new_val): show_snack(f"Güncellendi", False); target_veh[field_key] = new_val 
            else: show_snack("Güncelleme hatası", True)
        def editable_row(label, field_key):
            txt = ft.TextField(value=target_veh.get(field_key, ''), text_size=16, content_padding=5, border_color="transparent", bgcolor="transparent", color="white", width=150, on_change=date_formatter)
            txt.on_blur = lambda e: save_date_change(e, field_key) 
            return ft.Container(content=ft.Row([ft.Text(f"{label}:", weight="bold", width=100, color="#FFC107"), txt, ft.Icon(name="edit", size=16, color="grey")]), padding=5, bgcolor="#333", border_radius=5)
        info_col = ft.Column([ft.Text(f"ARAÇ: {target_veh.get('plaka')}", size=20, weight="bold", color="#FFC107"),read_only_row("Marka/Model", f"{target_veh.get('marka','')} {target_veh.get('model','')}"),read_only_row("Son KM", target_veh.get('km',''), ref=km_ref),ft.Divider(),read_only_row("Sigorta", target_veh.get('sigorta_tarihi','')),read_only_row("Kasko", target_veh.get('kasko_tarihi','')),editable_row("Muayene", "muayene_tarihi"),editable_row("Egzoz", "egzoz_tarihi")])
        randevular = normalize_list(target_veh.get('randevular', [])); randevu_col = ft.Column(spacing=2)
        def render_randevular():
            randevu_col.controls.clear()
            if not randevular: randevu_col.controls.append(ft.Text("Planlanmış randevu yok.", color="grey", italic=True))
            else:
                for idx, r in enumerate(reversed(randevular)):
                    real_idx = len(randevular) - 1 - idx
                    icon = "check_circle" if r.get('durum') == 'Tamamlandı' else "access_time"
                    color = "green" if r.get('durum') == 'Tamamlandı' else "orange"
                    def del_rand(e, ri=real_idx):
                        del randevular[ri]
                        if update_data(f"araclar/{target_idx}/randevular", randevular): render_randevular(); show_snack("Silindi")
                    def toggle_rand(e, ri=real_idx):
                        if randevular[ri]['durum'] == "Bekliyor": randevular[ri]['durum'] = "Tamamlandı"
                        else: randevular[ri]['durum'] = "Bekliyor"
                        if update_data(f"araclar/{target_idx}/randevular", randevular): render_randevular()
                    tile = ft.ListTile(leading=ft.Icon(name=icon, color=color),title=ft.Text(f"{r.get('tarih')} - {r.get('aciklama')}", color="white"),subtitle=ft.Text(f"Durum: {r.get('durum')}", color=color, size=12),trailing=ft.PopupMenuButton(items=[ft.PopupMenuItem(text="Durum Değiştir", on_click=lambda e, ri=real_idx: toggle_rand(e, ri)), ft.PopupMenuItem(text="Sil", icon="delete", on_click=lambda e, ri=real_idx: del_rand(e, ri))]))
                    randevu_col.controls.append(ft.Container(content=tile, bgcolor="#333", border_radius=5, padding=0))
            page.update()
        def add_randevu_dialog(e):
            r_tarih = ft.TextField(label="Tarih (GG.AA.YYYY)", value=datetime.now().strftime("%d.%m.%Y"), on_change=date_formatter)
            r_desc = ft.TextField(label="Açıklama / İşlem")
            def save_r(e):
                if not r_tarih.value or not r_desc.value: return
                new_r = {"tarih": r_tarih.value, "aciklama": r_desc.value, "durum": "Bekliyor"}
                randevular.append(new_r)
                if update_data(f"araclar/{target_idx}/randevular", randevular): render_randevular(); page.close(dlg_r); show_snack("Randevu Eklendi")
            dlg_r = ft.AlertDialog(title=ft.Text("Yeni Randevu"), content=ft.Column([r_tarih, r_desc], height=150), actions=[ft.ElevatedButton("KAYDET", on_click=save_r)]); page.open(dlg_r)
        render_randevular()
        harcamalar = normalize_list(target_veh.get('harcamalar', [])); hist_col = ft.Column(spacing=2)
        def render_history():
            hist_col.controls.clear(); total = 0.0
            for h in reversed(harcamalar): 
                try: total += float(str(h.get('tutar',0)).replace(" TL","").replace(".","").replace(",","."));
                except: pass
                km_bilgi = f" ({h.get('km', '?')} km)" if h.get('km') else ""
                hist_col.controls.append(ft.Container(content=ft.Row([ft.Text(h.get('tarih'), width=80, size=12, color="grey"), ft.Text(f"{h.get('aciklama')}{km_bilgi}", expand=True, weight="bold"), ft.Text(f"{h.get('tutar')} TL", width=80, text_align="right", color="#4CAF50")]), padding=10, bgcolor="#333", border_radius=5))
            hist_col.controls.insert(0, ft.Text(f"Toplam: {total:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", "."), color="#4CAF50", weight="bold", size=16, text_align="right")); page.update()
        render_history()
        t_tarih = ft.TextField(label="Tarih", value=datetime.now().strftime("%d.%m.%Y"), width=120, on_change=date_formatter)
        t_desc = ft.TextField(label="İşlem / Açıklama", expand=True)
        t_price = ft.TextField(label="Tutar", width=120, keyboard_type=ft.KeyboardType.NUMBER, on_blur=currency_formatter)
        t_km = ft.TextField(label="KM", width=100, keyboard_type=ft.KeyboardType.NUMBER) 
        def add_expense(e):
            if not t_desc.value or not t_price.value: return
            if t_km.value.strip(): 
                update_data(f"araclar/{target_idx}/km", t_km.value.strip())
                if km_ref.current: km_ref.current.value = t_km.value; km_ref.current.update()
            formatted_price = t_price.value if "TL" in t_price.value else t_price.value 
            new_exp = {"tarih": t_tarih.value, "aciklama": t_desc.value, "tutar": formatted_price, "km": t_km.value}
            harcamalar.append(new_exp)
            if update_data(f"araclar/{target_idx}/harcamalar", harcamalar): show_snack("Kaydedildi", False); t_desc.value=""; t_price.value=""; t_km.value=""; target_veh['harcamalar']=harcamalar; render_history()
        randevu_box = ft.Container(content=ft.Column([ft.Row([ft.Text("RANDEVULAR", weight="bold", size=16), ft.IconButton(icon="add_circle", icon_color="green", on_click=add_randevu_dialog)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), randevu_col]), padding=10, bgcolor="#222", border_radius=10, margin=ft.margin.only(top=10, bottom=10))
        add_box = ft.Container(content=ft.Column([ft.Text("YENİ HARCAMA", weight="bold", color="white"), ft.Row([t_tarih, t_price, t_km]), t_desc, ft.ElevatedButton("KAYDET", on_click=add_expense, bgcolor="green", color="white", width=400)]), padding=10, bgcolor="#2b2b2b", border_radius=10, border=ft.border.all(1, "grey"))
        return ft.Column([info_col, ft.Divider(), randevu_box, add_box, ft.Text("Geçmiş Harcamalar", weight="bold", size=16), ft.Container(content=hist_col, expand=True)], scroll=ft.ScrollMode.AUTO, expand=True)

    # --- SAHALAR ---
    def create_sahalar_view():
        data = normalize_list(get_data("musteriler")); list_col = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, expand=True)
        def render(st=""):
            list_col.controls.clear(); val = normalize_search_text(st)
            for i, m in enumerate(data):
                if m and val in normalize_search_text(m.get('ad','')):
                    list_col.controls.append(ft.Card(content=ft.ListTile(leading=ft.Icon(name="business", color="blue"), title=ft.Text(m.get('ad')), subtitle=ft.Text(f"Saha: {len(normalize_list(m.get('alanlar', [])))}"), trailing=ft.Icon(name="arrow_forward_ios", size=14), on_click=lambda e, mus=m, idx=i: show_musteri_detail(mus, idx)), color=COLOR_CARD))
            page.update()
        def add_cust(e):
            c_name = ft.TextField(label="Müşteri Adı")
            def save(e):
                if not c_name.value: return
                new = {"ad": c_name.value, "alanlar": [], "added_by": CURRENT_USER['name']}; cur = normalize_list(get_data("musteriler")); cur.append(new)
                if update_data("musteriler", cur): show_snack("Eklendi", False); page.close(dlg); data.append(new); render()
            dlg = ft.AlertDialog(title=ft.Text("Müşteri Ekle"), content=c_name, actions=[ft.ElevatedButton("KAYDET", on_click=save)]); page.open(dlg)
        render()
        return ft.Column([ft.Container(content=ft.ElevatedButton(" + MÜŞTERİ EKLE", icon="domain_add", bgcolor="blue", color="white", width=300, on_click=add_cust), alignment=ft.alignment.center, padding=10), ft.TextField(label="Müşteri Ara...", prefix_icon="search", on_change=lambda e: render(e.control.value)), list_col], expand=True)

    def update_generator_info_dialog(alan, cust_idx, field_idx, refresh_callback):
        servisler = normalize_list(alan.get('servisler', [])); last_srv = servisler[-1] if servisler else {}; last_filt = last_srv.get('filtreler', {}) if isinstance(last_srv.get('filtreler'), dict) else {}
        def v(key, srv_key): val = alan.get(key); return val if val and str(val).strip() != "" else last_srv.get(srv_key, "")
        def f(key, filt_key): val = alan.get(key); return val if val and str(val).strip() != "" else last_filt.get(filt_key, "")
        guc = ft.TextField(label="Güç", value=v('guc','guc')); marka = ft.TextField(label="Marka", value=v('marka','marka')); model = ft.TextField(label="Model", value=v('model','model'))
        motor = ft.TextField(label="Motor", value=v('motor','motor')); alt = ft.TextField(label="Alt.", value=v('alternator','alternator')); kontrol = ft.TextField(label="Kontrol", value=v('kontrol_cihazi','kontrol_cihazi'))
        seri = ft.TextField(label="Seri No", value=v('set_seri_no','set_seri_no')); aku_m = ft.TextField(label="Akü Mrk", value=v('aku_marka','aku_marka')); aku_a = ft.TextField(label="Akü Adet", value=v('aku_akimi','aku_akimi'))
        mot_kap = ft.TextField(label="Mot. Yağ Kap. (Lt)", value=v('motor_yag_kapasitesi', 'motor_yag_kapasitesi'))
        yag_k = ft.TextField(label="Yağ F.", value=f('yag_filtresi','yag_kodu'), col=8); yag_a = ft.TextField(label="Adet", value=f('yag_adet','yag_adet'), col=4)
        yakit_k = ft.TextField(label="Yakıt F.", value=f('yakit_filtresi','yakit_kodu'), col=8); yakit_a = ft.TextField(label="Adet", value=f('yakit_adet','yakit_adet'), col=4)
        hava_k = ft.TextField(label="Hava F.", value=f('hava_filtresi','hava_kodu'), col=8); hava_a = ft.TextField(label="Adet", value=f('hava_adet','hava_adet'), col=4)
        sep_k = ft.TextField(label="Sep. Kod", value=f('seperator_kodu','seperator_kodu'), col=8); sep_a = ft.TextField(label="Adet", value=f('seperator_adet','seperator_adet'), col=4)
        def save(e):
            alan.update({'guc': guc.value, 'marka': marka.value, 'model': model.value, 'motor': motor.value, 'alternator': alt.value, 'kontrol_cihazi': kontrol.value, 'set_seri_no': seri.value, 'aku_marka': aku_m.value, 'aku_akimi': aku_a.value, 'motor_yag_kapasitesi': mot_kap.value, 'yag_filtresi': yag_k.value, 'yag_adet': yag_a.value, 'yakit_filtresi': yakit_k.value, 'yakit_adet': yakit_a.value, 'hava_filtresi': hava_k.value, 'hava_adet': hava_a.value, 'seperator_kodu': sep_k.value, 'seperator_adet': sep_a.value})
            if update_data(f"musteriler/{cust_idx}/alanlar/{field_idx}", alan): show_snack("Güncellendi", False); page.close(dlg); refresh_callback()
            else: show_snack("Hata", True)
        col = ft.Column([ft.Text("Makine Bilgileri", color="yellow"), guc, marka, model, motor, alt, kontrol, seri, mot_kap, aku_m, aku_a, ft.Divider(), ft.Text("Filtreler", color="yellow"), ft.ResponsiveRow([yag_k, yag_a]), ft.ResponsiveRow([yakit_k, yakit_a]), ft.ResponsiveRow([hava_k, hava_a]), ft.ResponsiveRow([sep_k, sep_a])], scroll=ft.ScrollMode.AUTO, height=500)
        dlg = ft.AlertDialog(title=ft.Text("Bilgileri Düzenle"), content=col, actions=[ft.ElevatedButton("KAYDET", on_click=save)]); page.open(dlg)

    def edit_alan_details_dialog(alan, cust_idx, field_idx, refresh_callback):
        adi = ft.TextField(label="Alan Adı", value=alan.get('adi')); kod = ft.TextField(label="Saha Kodu", value=alan.get('kod')); bolge = ft.TextField(label="Bölge", value=alan.get('bolge')); il = ft.TextField(label="İl", value=alan.get('il')); ilce = ft.TextField(label="İlçe", value=alan.get('ilce')); adres = ft.TextField(label="Adres", value=alan.get('adres'), multiline=True); tel = ft.TextField(label="Telefon", value=alan.get('telefon')); enlem = ft.TextField(label="Enlem", value=alan.get('enlem')); boylam = ft.TextField(label="Boylam", value=alan.get('boylam'))
        def save(e):
            alan.update({'adi': adi.value, 'kod': kod.value, 'bolge': bolge.value, 'il': il.value, 'ilce': ilce.value, 'adres': adres.value, 'telefon': tel.value, 'enlem': enlem.value, 'boylam': boylam.value})
            if update_data(f"musteriler/{cust_idx}/alanlar/{field_idx}", alan): show_snack("Güncellendi", False); page.close(dlg); refresh_callback()
            else: show_snack("Hata", True)
        content = ft.Column([adi, kod, bolge, il, ilce, adres, tel, enlem, boylam], scroll=ft.ScrollMode.AUTO, height=500)
        dlg = ft.AlertDialog(title=ft.Text("Saha Düzenle"), content=content, actions=[ft.ElevatedButton("KAYDET", on_click=save)]); page.open(dlg)

    def show_alan_detail(alan, cust_idx, field_idx):
        if isinstance(alan, list) and len(alan) > 0: alan = alan[0]
        elif isinstance(alan, list): return
        def refresh_page(): 
            new = get_data(f"musteriler/{cust_idx}/alanlar/{field_idx}")
            if isinstance(new, list) and len(new) > 0: new = new[0]
            if new: page.views.pop(); show_alan_detail(new, cust_idx, field_idx)
        srvs = normalize_list(alan.get('servisler', [])); last_srv = srvs[-1] if srvs else {}; last_filt = last_srv.get('filtreler', {}) if isinstance(last_srv.get('filtreler'), dict) else {}
        def v(k, sk): val = alan.get(k); return val if val else last_srv.get(sk, "")
        def f(k, fk): val = alan.get(k); return val if val else last_filt.get(fk, "")
        info_col = ft.Column([detail_row("Kod", alan.get('kod')), detail_row("Güç", v('guc','guc')), detail_row("Marka", v('marka','marka')), detail_row("Model", v('model','model')), detail_row("Seri", v('set_seri_no','set_seri_no')), detail_row("Yağ Kap.", v('motor_yag_kapasitesi', 'motor_yag_kapasitesi')), detail_row("Adres", f"{alan.get('ilce','')}/{alan.get('il','')}"), detail_row("Filtreler", f"Y:{f('yag_filtresi','yag_kodu')} Yk:{f('yakit_filtresi','yakit_kodu')} H:{f('hava_filtresi','hava_kodu')}")])
        srv_list = ft.Column(spacing=5); 
        if srvs:
            for s in reversed(srvs): srv_list.controls.append(ft.Card(content=ft.ListTile(title=ft.Text(s.get('tarih'), color="green"), subtitle=ft.Text(f"{s.get('aciklama')}\n({s.get('user','?')})", size=12)), color=COLOR_CARD))
        else: srv_list.controls.append(ft.Text("Kayıt yok."))
        has_coords = bool(alan.get('enlem') and alan.get('boylam'))
        def open_map(e): 
            if has_coords: 
                safe_open_file(f"https://www.google.com/maps/search/?api=1&query={str(alan.get('enlem')).replace(',', '.')},{str(alan.get('boylam')).replace(',', '.')}")
            else: show_snack("Konum yok!", True)
        btn_map = ft.ElevatedButton("HARİTA", icon="map", bgcolor="#1976D2" if has_coords else "grey", color="white" if has_coords else "black", expand=True, disabled=not has_coords, on_click=open_map)
        btn_edit = ft.ElevatedButton("DÜZENLE", icon="edit", expand=True, bgcolor="white", color="black", on_click=lambda e: edit_alan_details_dialog(alan, cust_idx, field_idx, refresh_page))
        page.views.append(ft.View(f"/alan_{cust_idx}_{field_idx}", [ft.AppBar(title=ft.Text(str(alan.get('adi') or 'Saha Detayı')), bgcolor=COLOR_PRIMARY), ft.Container(content=ft.Column([ft.Row([btn_edit, btn_map]), ft.ElevatedButton("JENERATÖR/FİLTRE GÜNCELLE", icon="build_circle", bgcolor="green", color="white", width=400, on_click=lambda e: update_generator_info_dialog(alan, cust_idx, field_idx, refresh_page)), ft.Divider(), ft.Text("TEKNİK BİLGİLER", weight="bold"), info_col, ft.Divider(), ft.Text("SERVİS GEÇMİŞİ", weight="bold"), srv_list], scroll=ft.ScrollMode.AUTO), padding=10, expand=True)], bgcolor=COLOR_BG)); page.update()

    def show_musteri_detail(musteri, cust_idx):
        def add_alan_click(e):
            adi = ft.TextField(label="Alan Adı"); kod = ft.TextField(label="Saha Kodu"); bolge = ft.TextField(label="Bölge"); il = ft.TextField(label="İl"); ilce = ft.TextField(label="İlçe"); adres = ft.TextField(label="Adres", multiline=True); tel = ft.TextField(label="Telefon"); lat = ft.TextField(label="Enlem"); lng = ft.TextField(label="Boylam")
            def save_alan(e):
                if not adi.value: return
                new = {"adi": adi.value, "kod": kod.value, "bolge": bolge.value, "il": il.value, "ilce": ilce.value, "adres": adres.value, "telefon": tel.value, "enlem": lat.value, "boylam": lng.value, "added_by": CURRENT_USER['name'], "yapilacaklar": [], "servisler": []}
                cur = normalize_list(musteri.get('alanlar', [])); cur.append(new)
                if update_data(f"musteriler/{cust_idx}/alanlar", cur): show_snack("Eklendi", False); page.close(dlg); musteri['alanlar'] = cur; show_musteri_detail(musteri, cust_idx)
            dlg = ft.AlertDialog(title=ft.Text("Yeni Saha"), content=ft.Column([adi, kod, bolge, il, ilce, adres, tel, ft.Row([lat, lng])], scroll=ft.ScrollMode.AUTO, height=400), actions=[ft.ElevatedButton("EKLE", on_click=save_alan)]); page.open(dlg)
        alanlar_col = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, expand=True)
        def render(st=""):
            alanlar_col.controls.clear(); val = normalize_search_text(st)
            for i, a in enumerate(normalize_list(musteri.get('alanlar', []))):
                if not a: continue
                search_source = (str(a.get('adi', '')) + " " + str(a.get('kod', '')) + " " + str(a.get('bolge', '')) + " " + str(a.get('guc', '')) + " " + str(a.get('marka', '')) + " " + str(a.get('model', '')) + " " + str(a.get('motor', '')))
                if val in normalize_search_text(search_source):
                    alanlar_col.controls.append(ft.Card(content=ft.ListTile(leading=ft.Icon(name="location_on", color="red"), title=ft.Text(a.get('adi')), subtitle=ft.Text(f"{a.get('kod', '')} - {a.get('bolge', '')}"), trailing=ft.Icon(name="arrow_forward"), on_click=lambda e, al=a, ix=i: show_alan_detail(al, cust_idx, ix)), color=COLOR_CARD))
            page.update()
        render()
        page.views.append(ft.View(f"/cust_{cust_idx}", [ft.AppBar(title=ft.Text(musteri.get('ad')), bgcolor=COLOR_PRIMARY), ft.Container(content=ft.Column([ft.Container(content=ft.ElevatedButton(" + ALAN EKLE", icon="add_location", bgcolor="#FFC107", color="black", width=300, on_click=add_alan_click), alignment=ft.alignment.center, padding=10), ft.TextField(label="Saha Ara (İsim, Kod, Bölge, Marka...)", prefix_icon="search", on_change=lambda e: render(e.control.value)), alanlar_col], expand=True), padding=10, expand=True)], bgcolor=COLOR_BG)); page.update()
    
    # --- YÖNETİM PANELİ ---
    def create_management_view():
        def build_arac_list():
            araclar = normalize_list(get_data("araclar")); col = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, expand=True)
            search_box = ft.TextField(label="Araç Ara...", prefix_icon="search", on_change=lambda e: render_cars(e.control.value))
            all_personnel = normalize_list(get_data("personel"))
            p_options = [ft.dropdown.Option(text=f"{p.get('ad')} {p.get('soyad')}") for p in all_personnel if p]
            p_options.insert(0, ft.dropdown.Option(text="")) 
            def render_cars(st=""):
                col.controls.clear(); val = normalize_search_text(st)
                for i, a in enumerate(araclar):
                    if not a: continue
                    if val in normalize_search_text(a.get('plaka','')) or val in normalize_search_text(a.get('zimmetli_personel','')):
                        tile = ft.ListTile(leading=ft.Icon(name="directions_car", color="orange"), title=ft.Text(a.get('plaka')), subtitle=ft.Text(f"{a.get('marka')} - {a.get('zimmetli_personel') or 'Boşta'}"), on_click=lambda e, ix=i: edit_full_vehicle_dialog(ix))
                        col.controls.append(ft.Card(content=tile, color=COLOR_CARD))
                page.update()
            def edit_full_vehicle_dialog(idx):
                veh = araclar[idx]
                def info_box(title, val, ref=None):
                    return ft.Container(content=ft.Column([ft.Text(title, size=10, weight="bold", color="grey"), ft.Text(str(val).upper() if val else "-", size=14, weight="bold", color="white", ref=ref)], spacing=2), bgcolor="#222", padding=8, border_radius=5, expand=True)
                zimmet_ref = ft.Ref[ft.Text]()
                header = ft.Container(content=ft.Text("ARAÇ KİMLİK BİLGİLERİ", color="white", weight="bold", text_align="center"), bgcolor=COLOR_PRIMARY, padding=5, width=float("inf"))
                header2 = ft.Container(content=ft.Text("TAKİP BİLGİLERİ", color="white", weight="bold", text_align="center"), bgcolor=COLOR_PRIMARY, padding=5, width=float("inf"))
                row1 = ft.Row([info_box("PLAKA", veh.get('plaka')), info_box("MARKA", veh.get('marka')), info_box("MODEL", veh.get('model'))])
                row2 = ft.Row([info_box("YIL", veh.get('yil')), info_box("SERİ NO", veh.get('belge_seri')), info_box("TESCİL TARİHİ", veh.get('tescil_tarihi'))])
                row3 = ft.Row([info_box("ŞASE NO", veh.get('sase_no'))])
                row4 = ft.Row([info_box("SON KM", veh.get('km')), info_box("SİGORTA TARİHİ", veh.get('sigorta_tarihi')), info_box("KASKO TARİHİ", veh.get('kasko_tarihi'))])
                zimmet_box = ft.Container(content=ft.Column([ft.Text("PERSONEL", size=10, color="grey"), ft.Text(veh.get('zimmetli_personel', 'BOŞTA'), color="#FF9800", weight="bold", ref=zimmet_ref)], spacing=2), bgcolor="#222", padding=8, border_radius=5, expand=True)
                row5 = ft.Row([info_box("MUAYENE TARİHİ", veh.get('muayene_tarihi')), info_box("EGZOZ TARİHİ", veh.get('egzoz_tarihi')), zimmet_box])
                def open_edit_dialog(e):
                    t_plaka = ft.TextField(label="Plaka", value=veh.get('plaka')); t_marka = ft.TextField(label="Marka", value=veh.get('marka')); t_model = ft.TextField(label="Model", value=veh.get('model')); t_yil = ft.TextField(label="Yıl", value=veh.get('yil')); t_km = ft.TextField(label="KM", value=veh.get('km'))
                    t_muayene = ft.TextField(label="Muayene", value=veh.get('muayene_tarihi'), on_change=date_formatter)
                    t_sigorta = ft.TextField(label="Sigorta", value=veh.get('sigorta_tarihi'), on_change=date_formatter)
                    t_kasko = ft.TextField(label="Kasko", value=veh.get('kasko_tarihi'), on_change=date_formatter)
                    t_egzoz = ft.TextField(label="Egzoz", value=veh.get('egzoz_tarihi'), on_change=date_formatter)
                    def save_details(e):
                        veh.update({'plaka': tr_upper(t_plaka.value), 'marka': t_marka.value, 'model': t_model.value, 'yil': t_yil.value, 'km': t_km.value, 'muayene_tarihi': t_muayene.value, 'sigorta_tarihi': t_sigorta.value, 'kasko_tarihi': t_kasko.value, 'egzoz_tarihi': t_egzoz.value})
                        if update_data(f"araclar/{idx}", veh): show_snack("Bilgiler Güncellendi", False); page.close(dlg_edit); page.close(dlg_card); edit_full_vehicle_dialog(idx)
                    dlg_edit = ft.AlertDialog(title=ft.Text("BİLGİLERİ DÜZENLE"), content=ft.Column([t_plaka, t_marka, t_model, t_yil, t_km, t_muayene, t_sigorta, t_kasko, t_egzoz], scroll=ft.ScrollMode.AUTO, height=400), actions=[ft.ElevatedButton("KAYDET", on_click=save_details)])
                    page.open(dlg_edit)
                def open_assign_dialog(e):
                    dd_pers = ft.Dropdown(label="Personel Seç", options=p_options, value=veh.get('zimmetli_personel'))
                    def save_assign(e):
                        selected = dd_pers.value; veh['zimmetli_personel'] = selected
                        if update_data(f"araclar/{idx}/zimmetli_personel", selected): zimmet_ref.current.value = selected or "BOŞTA"; zimmet_ref.current.update(); show_snack("Personel Atandı", False); page.close(dlg_assign)
                    dlg_assign = ft.AlertDialog(title=ft.Text("PERSONEL ATA"), content=dd_pers, actions=[ft.ElevatedButton("KAYDET", on_click=save_assign)])
                    page.open(dlg_assign)
                btn_edit = ft.ElevatedButton("DÜZENLE", icon="edit", on_click=open_edit_dialog, expand=True)
                btn_assign = ft.ElevatedButton("PERSONEL ATA", icon="person_add", bgcolor="#00695C", color="white", on_click=open_assign_dialog, expand=True)
                dlg_card = ft.AlertDialog(content=ft.Column([header, row1, row2, row3, header2, row4, row5, ft.Divider(), ft.Row([btn_edit, btn_assign])], scroll=ft.ScrollMode.AUTO, height=600, width=400))
                page.open(dlg_card)
            def add_vehicle_dialog(e):
                plaka = ft.TextField(label="Plaka"); marka = ft.TextField(label="Marka"); model = ft.TextField(label="Model")
                def save(e):
                    if not plaka.value: return
                    new_veh = {"plaka": tr_upper(plaka.value), "marka": marka.value, "model": model.value, "harcamalar": [], "randevular": []}
                    araclar.append(new_veh)
                    if update_data("araclar", araclar): show_snack("Eklendi", False); page.close(dlg); render_cars()
                dlg = ft.AlertDialog(title=ft.Text("Yeni Araç"), content=ft.Column([plaka, marka, model], height=200), actions=[ft.ElevatedButton("KAYDET", on_click=save)]); page.open(dlg)
            render_cars()
            return ft.Column([ft.Container(content=ft.ElevatedButton("ARAÇ EKLE", icon="add", on_click=add_vehicle_dialog), padding=10), search_box, col], expand=True)
        
        def build_personel_list():
            pers = normalize_list(get_data("personel")); col = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, expand=True)
            search_box = ft.TextField(label="Personel Ara...", prefix_icon="search", on_change=lambda e: render_pers(e.control.value))
            def render_pers(st=""):
                col.controls.clear(); val = normalize_search_text(st)
                for i, p in enumerate(pers):
                    if not p: continue
                    full_name = f"{p.get('ad','')} {p.get('soyad','')}"
                    if val in normalize_search_text(full_name) or val in normalize_search_text(p.get('plaka','')):
                        col.controls.append(ft.Card(content=ft.ListTile(leading=ft.Icon(name="person", color="cyan"), title=ft.Text(full_name), subtitle=ft.Text(f"Plaka: {p.get('plaka','-')}"), on_click=lambda e, ix=i: edit_full_person_dialog(ix)), color=COLOR_CARD))
                page.update()
            def edit_full_person_dialog(idx):
                p = pers[idx]
                def info_box(title, val): return ft.Container(content=ft.Column([ft.Text(title, size=10, color="grey"), ft.Text(str(val), weight="bold", color="white")], spacing=2), bgcolor="#222", padding=8, border_radius=5, expand=True)
                header = ft.Container(content=ft.Text("PERSONEL KARTI", color="white", weight="bold", text_align="center"), bgcolor=COLOR_PRIMARY, padding=5, width=float("inf"))
                row1 = ft.Row([info_box("AD", p.get('ad')), info_box("SOYAD", p.get('soyad'))])
                row2 = ft.Row([info_box("TC NO", p.get('tc')), info_box("SİCİL", p.get('sicil_no'))])
                row3 = ft.Row([info_box("SERİ NO", p.get('seri_no')), info_box("DOĞUM", p.get('dogum_tarihi'))])
                row4 = ft.Row([info_box("İŞE GİRİŞ", p.get('ise_giris')), info_box("TELEFON", p.get('telefon'))])
                row5 = ft.Row([info_box("MAIL", p.get('email')), info_box("ŞİFRE", p.get('sifre'))])
                row6 = ft.Row([info_box("ARAÇ PLAKASI", p.get('plaka'))])
                def open_edit_dialog(e):
                    ad = ft.TextField(label="Ad", value=p.get('ad')); soyad = ft.TextField(label="Soyad", value=p.get('soyad')); tel = ft.TextField(label="Telefon", value=p.get('telefon')); mail = ft.TextField(label="Email", value=p.get('email')); sifre = ft.TextField(label="Şifre", value=p.get('sifre')); plaka = ft.TextField(label="Araç Plakası", value=p.get('plaka'))
                    tc = ft.TextField(label="TC No", value=p.get('tc')); sicil = ft.TextField(label="Sicil No", value=p.get('sicil_no')); seri = ft.TextField(label="Seri No", value=p.get('seri_no')); giris = ft.TextField(label="İşe Giriş", value=p.get('ise_giris')); dogum = ft.TextField(label="Doğum Tarihi", value=p.get('dogum_tarihi'))
                    def save(e):
                        p.update({'ad': tr_upper(ad.value), 'soyad': tr_upper(soyad.value), 'telefon': tel.value, 'email': mail.value, 'sifre': sifre.value, 'plaka': tr_upper(plaka.value), 'tc': tc.value, 'sicil_no': sicil.value, 'seri_no': seri.value, 'ise_giris': giris.value, 'dogum_tarihi': dogum.value})
                        if update_data(f"personel/{idx}", p): update_firebase_user_plate(mail.value, tr_upper(plaka.value)); show_snack("Güncellendi", False); page.close(dlg_edit); page.close(dlg_card); edit_full_person_dialog(idx)
                    dlg_edit = ft.AlertDialog(title=ft.Text("DÜZENLE"), content=ft.Column([ad, soyad, tc, sicil, seri, giris, dogum, tel, mail, sifre, plaka], scroll=ft.ScrollMode.AUTO, height=400), actions=[ft.ElevatedButton("KAYDET", on_click=save)])
                    page.open(dlg_edit)
                btn_edit = ft.ElevatedButton("BİLGİLERİ DÜZENLE", icon="edit", on_click=open_edit_dialog, expand=True)
                dlg_card = ft.AlertDialog(content=ft.Column([header, row1, row2, row3, row4, row5, row6, ft.Divider(), btn_edit], height=500, width=350))
                page.open(dlg_card)
            def add_person_dialog(e):
                ad = ft.TextField(label="Ad"); soyad = ft.TextField(label="Soyad"); mail = ft.TextField(label="Email"); sifre = ft.TextField(label="Şifre")
                def save(e):
                    if not ad.value: return
                    new_p = {"ad": tr_upper(ad.value), "soyad": tr_upper(soyad.value), "email": mail.value, "sifre": sifre.value, "plaka": ""}
                    pers.append(new_p)
                    if update_data("personel", pers): show_snack("Eklendi", False); page.close(dlg); render_pers()
                dlg = ft.AlertDialog(title=ft.Text("Yeni Personel"), content=ft.Column([ad, soyad, mail, sifre], height=300), actions=[ft.ElevatedButton("KAYDET", on_click=save)]); page.open(dlg)
            render_pers()
            return ft.Column([ft.Container(content=ft.ElevatedButton("PERSONEL EKLE", icon="person_add", on_click=add_person_dialog), padding=10), search_box, col], expand=True)
        
        # -- 3. SAHA GÖREV YÖNETİMİ --
        def build_saha_gorev_yonetimi():
            all_gorevler = normalize_list(get_data("saha_gorevleri"))
            list_col = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, expand=True)
            search_box = ft.TextField(label="Görev Ara (Kod, Müşteri, Personel)...", prefix_icon="search", on_change=lambda e: render_gorev(e.control.value))
            
            all_personnel = normalize_list(get_data("personel"))
            p_options = [ft.dropdown.Option(text=f"{p.get('ad')} {p.get('soyad')}") for p in all_personnel if p]
            
            all_fields_flat = []
            cust_data = normalize_list(get_data("musteriler"))
            for c in cust_data:
                c_name = c.get('ad', 'Bilinmiyor')
                for f in normalize_list(c.get('alanlar', [])):
                    if f:
                        all_fields_flat.append({
                            "musteri": c_name,
                            "kod": f.get('kod', ''),
                            "ad": f.get('adi', ''),
                            "search_key": f"{f.get('kod', '')} {f.get('adi', '')} {c_name}".lower()
                        })

            def render_gorev(st=""):
                list_col.controls.clear()
                val = normalize_search_text(st)
                
                sorted_tasks = sorted(enumerate(all_gorevler), key=lambda x: x[1].get('id', '0'), reverse=True)

                for i, t in sorted_tasks:
                    if not t: continue
                    search_source = f"{t.get('kod','')} {t.get('musteri','')} {t.get('ad','')} {t.get('personel','')}"
                    if val in normalize_search_text(search_source):
                        is_done = t.get('tamamlandi', False)
                        color = "green" if is_done else "orange"
                        icon = "check_circle" if is_done else "pending"
                        
                        card = ft.Card(
                            content=ft.ListTile(
                                leading=ft.Icon(name=icon, color=color),
                                title=ft.Text(f"{t.get('kod')} - {t.get('ad')}", weight="bold"),
                                subtitle=ft.Text(f"{t.get('musteri')}\nPer: {t.get('personel')}\n{t.get('tarih')}", size=12),
                                trailing=ft.IconButton(icon="delete", icon_color="red", on_click=lambda e, ix=i: delete_gorev(ix)),
                                on_click=lambda e, ix=i: edit_gorev_dialog(ix)
                            ),
                            color=COLOR_CARD
                        )
                        list_col.controls.append(card)
                page.update()

            def delete_gorev(idx):
                def action():
                    del all_gorevler[idx]
                    if update_data("saha_gorevleri", all_gorevler):
                        show_snack("Görev Silindi", False)
                        render_gorev(search_box.value)
                confirm_action("Sil", "Bu iş emri silinsin mi?", action)

            def add_gorev_dialog(e):
                selected_field = [None]
                search_field = ft.TextField(label="Saha/Müşteri Ara", autofocus=True)
                field_list = ft.Column(scroll=ft.ScrollMode.AUTO) # Height kaldırıldı
                
                tarih = ft.TextField(label="Tarih", value=datetime.now().strftime("%d.%m.%Y"), on_change=date_formatter)
                personel = ft.Dropdown(label="Personel Seç", options=p_options)
                # Açıklama alanı büyütüldü
                aciklama = ft.TextField(label="Açıklama", multiline=True, min_lines=4)

                def do_field_search(e):
                    val = normalize_search_text(search_field.value)
                    field_list.controls.clear()
                    if len(val) < 2: 
                        page.update()
                        return
                    
                    count = 0
                    for item in all_fields_flat:
                        if count > 20: break
                        if val in item['search_key']:
                            def select_f(e, x=item):
                                selected_field[0] = x
                                search_field.value = f"{x['kod']} - {x['ad']}"
                                search_field.disabled = True
                                field_list.controls.clear()
                                page.update()
                                
                            tile = ft.ListTile(
                                title=ft.Text(f"{item['kod']} - {item['ad']}"),
                                subtitle=ft.Text(item['musteri']),
                                on_click=select_f
                            )
                            field_list.controls.append(tile)
                            count += 1
                    page.update()

                search_field.on_change = do_field_search

                def save(e):
                    if not selected_field[0] or not aciklama.value:
                        show_snack("Saha ve Açıklama zorunludur", True)
                        return
                    
                    new_id = f"#{len(all_gorevler) + 1:04d}"
                    new_task = {
                        "id": new_id,
                        "musteri": selected_field[0]['musteri'],
                        "kod": selected_field[0]['kod'],
                        "ad": selected_field[0]['ad'],
                        "personel": personel.value,
                        "tarih": tarih.value,
                        "aciklama": aciklama.value,
                        "tamamlandi": False,
                        "ekleme_zamani": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    
                    all_gorevler.append(new_task)
                    if update_data("saha_gorevleri", all_gorevler):
                        show_snack("Görev Eklendi", False)
                        page.close(dlg)
                        render_gorev()

                # Boşluk azaltıldı, field_list artık yer kaplamıyor boşken
                dlg = ft.AlertDialog(
                    title=ft.Text("Yeni İş Emri"),
                    content=ft.Column([
                        search_field, 
                        field_list, # Sadece sonuç varsa yer kaplar
                        tarih, 
                        personel, 
                        aciklama
                    ], spacing=10, height=450, scroll=ft.ScrollMode.AUTO),
                    actions=[ft.ElevatedButton("KAYDET", on_click=save)]
                )
                page.open(dlg)

            def edit_gorev_dialog(idx):
                t = all_gorevler[idx]
                personel = ft.Dropdown(label="Personel", options=p_options, value=t.get('personel'))
                aciklama = ft.TextField(label="Açıklama", value=t.get('aciklama'), multiline=True)
                
                def save(e):
                    t['personel'] = personel.value
                    t['aciklama'] = aciklama.value
                    if update_data(f"saha_gorevleri/{idx}", t):
                        show_snack("Güncellendi", False)
                        page.close(dlg)
                        render_gorev(search_box.value)
                
                dlg = ft.AlertDialog(
                    title=ft.Text("Düzenle"),
                    content=ft.Column([
                        ft.Text(f"{t.get('kod')} - {t.get('ad')}", weight="bold"),
                        personel, aciklama
                    ], height=250),
                    actions=[ft.ElevatedButton("KAYDET", on_click=save)]
                )
                page.open(dlg)

            render_gorev()
            return ft.Column([
                ft.Container(content=ft.ElevatedButton("YENİ GÖREV EKLE", icon="add_task", bgcolor="#F57C00", color="white", on_click=add_gorev_dialog), padding=10),
                search_box,
                list_col
            ], expand=True)

        # Tab sıralaması değiştirildi
        return ft.Tabs(selected_index=0, tabs=[
            ft.Tab(text="ARAÇLAR", icon="directions_car", content=build_arac_list()),
            ft.Tab(text="PERSONEL", icon="group", content=build_personel_list()),
            ft.Tab(text="İŞ EMİRLERİ", icon="assignment", content=build_saha_gorev_yonetimi())
        ])

    # --- ANA EKRAN GÖSTERİMİ ---
    def show_main_app():
        tabs = [
            ft.Tab(text="SAHA", icon="business", content=create_sahalar_view()),
            ft.Tab(text="GÖREVLER", icon="assignment_ind", content=create_my_tasks_view()),
            ft.Tab(text="İŞ TAKİP", icon="task_alt", content=create_is_takip_view()),
            ft.Tab(text="ARACIM", icon="directions_car", content=create_my_vehicle_view())
        ]
        
        if CURRENT_USER['role'] == 'admin':
            tabs.append(ft.Tab(text="YÖNETİM", icon="settings", content=create_management_view()))
            
        def logout(e): 
            CURRENT_USER["email"] = None; 
            CURRENT_USER["token"] = None; 
            page.client_storage.remove("saved_pass"); 
            show_login_screen()
            
        page.views.clear()
        page.views.append(ft.View("/", [
            ft.AppBar(
                title=ft.Text(f"Galata ({CURRENT_USER.get('name', '')})"), 
                bgcolor=COLOR_PRIMARY, 
                actions=[ft.IconButton(icon="logout", on_click=logout)]
            ), 
            ft.Tabs(tabs=tabs, expand=True, indicator_color="white")
        ], bgcolor=COLOR_BG))
        page.update()
        
        check_daily_reminders()

    # --- LOGIN EKRANI ---
    def show_login_screen():
        page.views.clear()
        saved_email = page.client_storage.get("saved_email"); saved_pass = page.client_storage.get("saved_pass")
        email_inp = ft.TextField(label="Kullanıcı Adı veya E-Mail", value=saved_email or "", prefix_icon="person", width=300)
        pass_inp = ft.TextField(label="Şifre", value=saved_pass or "", password=True, can_reveal_password=True, prefix_icon="lock", width=300)
        
        rem_chk = ft.Row([ft.Checkbox(label="Beni Hatırla", value=True if saved_email else False)], alignment=ft.MainAxisAlignment.CENTER)

        def do_login(e):
            input_val = normalize_search_text(email_inp.value)
            pass_val = pass_inp.value
            if not input_val or not pass_val: show_snack("Bilgileri giriniz", True); return
            
            auth_res = login_with_firebase(email_inp.value, pass_val)
            
            if auth_res:
                id_token = auth_res['idToken']
                CURRENT_USER["token"] = id_token
                CURRENT_USER["email"] = email_inp.value
            else:
                show_snack("Giriş Başarısız! E-mail/Şifre hatalı veya kullanıcı yok.", True)
                return

            CURRENT_USER.update({"role": None, "name": None, "plate": None})
            found = None
            users = get_data("kullanicilar")
            
            if users:
                for v in users.values():
                    if (normalize_search_text(v.get('email', '')) == input_val):
                        found = v
                        role_val = v.get('role') or v.get('rol') 
                        name_val = v.get('ad_soyad') or v.get('ad') 
                        if str(role_val).upper() == "YÖNETİCİ": role_val = "admin"
                        CURRENT_USER.update({"role": role_val, "name": name_val, "plate": v.get('plaka') or v.get('yetkili_plaka')})
                        break
            
            if not found:
                for p in normalize_list(get_data("personel")):
                    if (normalize_search_text(p.get('email', '')) == input_val):
                        found = p
                        CURRENT_USER.update({"role": "personel", "name": p.get('ad'), "plate": p.get('plaka') or p.get('yetkili_plaka')})
                        break

            if found:
                if rem_chk.controls[0].value: 
                    page.client_storage.set("saved_email", email_inp.value)
                    page.client_storage.set("saved_pass", pass_inp.value)
                else: 
                    page.client_storage.remove("saved_email")
                    page.client_storage.remove("saved_pass")
                show_main_app()
            else: 
                show_snack("Giriş yapıldı ancak veritabanında profil bulunamadı.", True)

        def forgot_password_click(e):
            fp_email = ft.TextField(label="E-Mail Adresiniz", prefix_icon="mail")
            def send_pass(e):
                if not fp_email.value: return
                url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_WEB_API_KEY}"
                payload = {"requestType": "PASSWORD_RESET", "email": fp_email.value}
                try:
                    r = requests.post(url, json=payload)
                    if r.status_code == 200:
                        show_snack("Şifre sıfırlama bağlantısı e-mailinize gönderildi.", False); page.close(dlg_fp)
                    else:
                        show_snack("Mail gönderilemedi veya adres kayıtlı değil.", True)
                except: show_snack("Hata oluştu.", True)

            dlg_fp = ft.AlertDialog(title=ft.Text("Şifremi Unuttum"), content=fp_email, actions=[ft.ElevatedButton("GÖNDER", on_click=send_pass)])
            page.open(dlg_fp)

        def change_password_click(e):
            cp_email = ft.TextField(label="E-Mail", prefix_icon="mail")
            cp_old = ft.TextField(label="Eski Şifre", password=True)
            cp_new = ft.TextField(label="Yeni Şifre", password=True)
            
            def update_pass(e):
                if not cp_email.value or not cp_old.value or not cp_new.value: return
                auth_res = login_with_firebase(cp_email.value, cp_old.value)
                if auth_res:
                    id_token = auth_res['idToken']
                    url = f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={FIREBASE_WEB_API_KEY}"
                    payload = {"idToken": id_token, "password": cp_new.value, "returnSecureToken": False}
                    try:
                        r = requests.post(url, json=payload)
                        if r.status_code == 200:
                            show_snack("Şifreniz başarıyla güncellendi.", False); page.close(dlg_cp)
                        else: show_snack("Güncelleme hatası.", True)
                    except: show_snack("Bağlantı hatası.", True)
                else:
                    show_snack("Eski şifre hatalı.", True)

            dlg_cp = ft.AlertDialog(title=ft.Text("Şifre Değiştir"), content=ft.Column([cp_email, cp_old, cp_new], height=200), actions=[ft.ElevatedButton("GÜNCELLE", on_click=update_pass)])
            page.open(dlg_cp)

        logo_content = ft.Image(src="/galata_logo.png", width=300, fit=ft.ImageFit.CONTAIN)

        login_btn = ft.ElevatedButton("GİRİŞ YAP", on_click=do_login, bgcolor=COLOR_PRIMARY, color="white", width=300)
        
        forgot_btn = ft.TextButton("Şifremi Unuttum", on_click=forgot_password_click)
        change_btn = ft.TextButton("Şifre Değiştir", on_click=change_password_click)
        
        page.views.append(ft.View("/login", [ft.Container(content=ft.Column([
            logo_content, 
            ft.Container(height=20), 
            email_inp, 
            pass_inp, 
            rem_chk, 
            login_btn, 
            ft.Row([forgot_btn, change_btn], alignment=ft.MainAxisAlignment.CENTER)
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), alignment=ft.alignment.center, expand=True)])); page.update()

    def check_auto_login():
        s_email = page.client_storage.get("saved_email"); s_pass = page.client_storage.get("saved_pass")
        if s_email and s_pass:
            auth_res = login_with_firebase(s_email, s_pass)
            if auth_res:
                CURRENT_USER["token"] = auth_res['idToken']
                CURRENT_USER["email"] = s_email
                found = None
                users = get_data("kullanicilar")
                if users:
                    for v in users.values():
                        if (normalize_search_text(v.get('email', '')) == normalize_search_text(s_email)): 
                            found = v
                            role_val = v.get('role') or v.get('rol') 
                            name_val = v.get('ad_soyad') or v.get('ad') 
                            if str(role_val).upper() == "YÖNETİCİ": role_val = "admin"
                            CURRENT_USER.update({"role": role_val, "name": name_val, "plate": v.get('plaka') or v.get('yetkili_plaka')}); break
                
                if not found:
                    for p in normalize_list(get_data("personel")):
                        if (normalize_search_text(p.get('email', '')) == normalize_search_text(s_email)): 
                            found = p; CURRENT_USER.update({"role": "personel", "name": p.get('ad'), "plate": p.get('plaka')}); break
                
                if found: show_main_app()
                else: show_login_screen()
            else: show_login_screen()
        else: show_login_screen()

    check_auto_login()

ft.app(target=main)
