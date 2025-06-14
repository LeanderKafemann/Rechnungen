import requests, datetime, random, os, pyperclip, webbrowser, threading, ping3
import pyautogui as py
from tkinter import *
from tkinter.filedialog import *
from naturalsize import reverse
from reportlab.pdfgen.canvas import Canvas as CanvasPdf
from reportlab.lib.units import cm

# --- Tooltip Hilfsklasse ---
class ToolTip:
    active = True
    all_tooltips = []
    def __init__(self, widget, text, always_show=False):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.visible = False
        self.always_show = always_show
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        ToolTip.all_tooltips.append(self)
    def enter(self, event=None):
        if ToolTip.active or self.always_show:
            self.schedule()
    def leave(self, event=None):
        self.unschedule()
        self.hidetip()
    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(350, self.showtip)
    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)
    def showtip(self, event=None):
        if self.tipwindow or not self.text or (not ToolTip.active and not self.always_show):
            return
        x, y = self.widget.winfo_pointerxy()
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x+10, y+10))
        label = Label(tw, text=self.text, justify=LEFT,
                      background="#ffffe0", relief=SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)
        self.visible = True
    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()
        self.visible = False
    @staticmethod
    def set_active(state: bool):
        ToolTip.active = state
        for t in ToolTip.all_tooltips:
            if not t.always_show:
                t.hidetip()

# --- Protokoll-Initialisierung und -Funktionen ---
def init_protocol():
    c.protocol_enabled = False
    c.protocol = []
    c.protocol_last_purpose = ""
    c.protocol_logged_start = False

def ask_protocol_activation():
    if c.time != [0, 0, 0, 0]:
        c.protocol_enabled = False
        return
    if py.confirm("Protokoll aktivieren? (Start-/Stopp-Zeiten & Zweck werden gespeichert)", "Protokoll", buttons=("Ja", "Nein")) == "Ja":
        c.protocol_enabled = True
        c.protocol_last_purpose = py.prompt("Was ist der Zweck der ersten Sitzung?", "Protokoll-Zweck", "")
        c.protocol = []
    else:
        c.protocol_enabled = False
        c.protocol_last_purpose = ""
        c.protocol = []

def log_protocol(event, purpose):
    if getattr(c, "protocol_enabled", False):
        now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        c.protocol.append(f"{event}: {now}\nZweck: {purpose}")
        update_protocol_window()

protocol_window = None
def open_protocol_window():
    global protocol_window
    if protocol_window and protocol_window.winfo_exists():
        protocol_window.lift()
        return
    protocol_window = Toplevel(window)
    protocol_window.title("Protokoll")
    protocol_window.geometry("400x200")
    protocol_window.resizable(False, False)
    protocol_window.configure(bg="light blue")
    Label(protocol_window, text="Protokoll (letzte 10 Einträge):", font=("Helvetica", 9, "bold"), bg="light blue").pack(anchor="w", padx=10, pady=(10,0))
    txt = Text(protocol_window, width=54, height=8, font=("Courier", 8), state="normal", bg="white", relief="solid", bd=1)
    txt.pack(padx=10, pady=5)
    txt.insert(END, "\n".join(c.protocol[-10:]) if c.protocol else "(Noch keine Einträge)")
    txt.config(state="disabled")
    ToolTip(txt, "Hier sehen Sie die letzten 10 Protokolleinträge (Start/Stop und Zweck).")
    protocol_window.protocol("WM_DELETE_WINDOW", protocol_window.destroy)
def update_protocol_window():
    global protocol_window
    if protocol_window and protocol_window.winfo_exists():
        for widget in protocol_window.winfo_children():
            if isinstance(widget, Text):
                widget.config(state="normal")
                widget.delete(1.0, END)
                widget.insert(END, "\n".join(c.protocol[-10:]) if c.protocol else "(Noch keine Einträge)")
                widget.config(state="disabled")

def split_text(text, max_len=75):
    # Teilt Text in Zeilen mit maximal max_len Zeichen
    import textwrap
    return textwrap.wrap(text, max_len)

def export():
    if not c.paused:
        pause_play()
    requests.post(c.basic_link+"uploader", {"pw": "lkunited", "message": "-"+c.id})
    text = ""
    today = datetime.datetime.today()
    td = today.date()
    tag = str(td.day)+"."+str(td.month)+"."+str(td.year)
    text += "\nRechnung vom "+tag+" an "+c.kunde
    zeit = format_time(c.time)
    text += "\ngearbeitete Zeit: "+zeit+" h"
    stunden = c.lohn_akt_uf
    text += "\nà "+format_money(c.lohn)+"/h entspricht das "+c.lohn_akt
    x = py.prompt("verbleibende Zahlungen (exkl. 10% Zins)?", "Export", "0.00")
    verbl = str(round(float(x)*1.1, ndigits=2)) if x != "" else "0.00"
    x = py.prompt("berechnete Pauschalen?", "Export", "0.00")
    pauschalen = x if x != "" else "0.0"
    text += "\nberechnete Pauschalen: "+format_money(pauschalen)
    text += "\nverbleibende Zahlungen (inkl. 10% Zins): "+format_money(verbl)
    text += "\nZu zahlen innerhalb von 7 Tagen."
    gesamt = str(float(stunden)+float(verbl)+float(pauschalen))
    text += "\nGesamtsumme: "+format_money(gesamt)
    ga = str(round(float(gesamt)*0.9995, ndigits=2))
    text += "\nDavon an "+c.name+": "+format_money(ga)
    abg = format_money(round(float(gesamt)-float(ga), ndigits=2))
    text += "\nDavon Abgaben an LK-Software (0.05%): "+abg
    text += "\nBemerkung: "+py.prompt("Bemerkung hinzufügen: ", "Bemerkung", "-")+"\ngezeichnet: "+c.name+" (umsatzsteuerbefreit)\n"
    xVar = max(34+len(c.name), 41+len(format_money(verbl)), 38+len(abg))
    copyright_line = "Made with LK Rechnungen - Copyright Leander Kafemann 2024-2025 - Version 2.0.0"
    text = xVar*"-"+text
    text += xVar * "-"
    protocol_text = ""
    if getattr(c, "protocol_enabled", False) and c.protocol:
        protocol_text += "\n\n" + xVar*"=" + "\nPROTOKOLL\n"
        for entry in c.protocol:
            protocol_text += entry + "\n"
        protocol_text += xVar*"=" + "\n"
        protocol_text += "\n" + copyright_line + "\n"
    filename = "./rechnung-"+tag+"-"+c.name+"-"+c.kunde
    if not c.protocol_enabled:
        py.alert("Hinweis: Das Protokoll ist für diese Rechnung deaktiviert.", "Protokoll-Hinweis")
    if py.confirm("Speichern als TXT oder PDF?", "Format", buttons=("TXT", "PDF")) == "TXT":
        with open(filename+".txt", "w", encoding="utf-8") as f:
            f.write(text)
            if protocol_text:
                f.write(protocol_text)
    else:
        c_ = CanvasPdf(filename+".pdf")
        c_.setFont("Courier-Bold", 30)
        c_.drawString(5*cm, 25*cm, "Exportierte Rechnung")
        c_.setFont("Courier", 15)
        y = 10*cm
        textList = text.split("\n")
        textList.reverse()
        for i in textList:
            c_.drawString(2*cm, y, i)
            y += cm
        c_.setFont("Courier-Bold", 22)
        c_.drawString(5.5*cm, 7*cm, "Gesamtsumme: "+format_money(gesamt))
        c_.setFont("Courier", 5)
        c_.drawString(7*cm, 2*cm, copyright_line)
        if protocol_text:
            c_.showPage()
            c_.setFont("Courier-Bold", 22)
            c_.drawString(2*cm, 27*cm, "Protokoll")
            c_.setFont("Courier", 13)
            y = 25*cm
            for entry in c.protocol:
                for subline in entry.splitlines():
                    for line in split_text(subline, 75):
                        if y < 2*cm:
                            c_.showPage()
                            y = 27*cm
                        c_.drawString(2*cm, y, line)
                        y -= 0.7*cm
            y -= 1*cm
            c_.setFont("Courier", 5)
            c_.drawString(7*cm, y, copyright_line)
        c_.save()
    print(text)
    py.alert("Rechnung erfolgreich exportiert.:\n"+text, "Export")
    quit()

def export_agent():
    c.after(1, export)

def update_time():
    if not c.paused:
        if c.time[3] < 8:
            c.time[3] += 2
        else:
            c.time[3] = 0
            if c.time[2] < 59:
                c.time[2] += 1
            else:
                c.time[2] = 0
                if c.time[1] < 59:
                    c.time[1] += 1
                else:
                    c.time[1] = 0
                    c.time[0] += 1
    c.itemconfig(c.time_text, text=format_time(c.time))
    c.after(195, update_time)

def update_lohn():
    zeit = format_time(c.time)
    zl = zeit.split(" : ")
    c.lohn_akt_uf = round(float(int(zl[0])+int(zl[1])/60+int(zl[2])/3600+int(zl[3])/36000)*c.lohn, ndigits=2)
    c.lohn_akt = format_money(c.lohn_akt_uf)
    c.itemconfig(c.lohn_text, text=c.lohn_akt)
    c.itemconfig(c.name_text, text="an "+c.name)
    c.after(200, update_lohn)

def pause_play():
    # Protokoll-Integration
    if not hasattr(c, "protocol_enabled"):
        c.protocol_enabled = False
    if not hasattr(c, "protocol"):
        c.protocol = []
    if not hasattr(c, "protocol_last_purpose"):
        c.protocol_last_purpose = ""
    if not hasattr(c, "protocol_logged_start"):
        c.protocol_logged_start = False

    c.paused = reverse(c.paused)
    c.status = "pausiert" if c.paused else "laufend"
    c.play_pause.config(activebackground="light green" if c.paused else "orange")
    if c.protocol_enabled:
        if not c.paused and not c.protocol_logged_start:
            purpose = py.prompt("Was machen Sie jetzt?", "Zweck der Sitzung", c.protocol_last_purpose)
            if purpose is None:
                purpose = c.protocol_last_purpose
            c.protocol_last_purpose = purpose
            log_protocol("Gestartet", purpose)
            c.protocol_logged_start = True
        elif c.paused and c.protocol_logged_start:
            log_protocol("Gestoppt", c.protocol_last_purpose)
            c.protocol_logged_start = False
    update_protocol_window()

def stop():
    if py.confirm("Wirklich ungespeichert beenden?", "Stop", buttons=("JA", "NEIN")) == "JA":
        requests.post(c.basic_link+"uploader", {"pw": "lkunited", "message": "-"+c.id})
        quit()

def share():
    c.share = True
    c.share_b.destroy()
    c.itemconfig(c.id_text, text=c.id)
    c.itemconfig(c.link_text, text=c.link)
    c.itemconfig(c.descr_text, text="Ihre ID und Link:")
    c.itemconfig(c.uptime_text, text="alle      s")
    c.itemconfig(c.uptime_text2, text="Upload")
    c.itemconfig(c.upload_time_text, text=str(c.upload_time))
    create_button()
    display_button()

def unshare():
    c.share = False
    requests.post(c.basic_link+"uploader", {"pw": "lkunited", "message": "-"+c.id})
    for i in [c.id_text, c.link_text, c.descr_text, c.uptime_text, c.uptime_text2, c.upload_time_text]:
        c.itemconfig(i, text="")
    for i in [c.copy_link_b, c.open_link_b, c.speedup_b, c.unshare_b]:
        i.destroy()
    create_button(False)
    display_button(False)

def unshare_agent():
    c.after(1, unshare)

def copy_link():
    pyperclip.copy(c.link)

def open_link():
    webbrowser.open(c.link)

def speedup():
    if c.upload_time < 60:
        c.speedup *= 1.5; c.speedup_v = True
        c.upload_time += int(c.speedup)
        if c.upload_time > 60:
            c.upload_time = 60
        c.after(500, reset_speedup)
    else:
        c.upload_time = 3
    c.itemconfig(c.upload_time_text, text=str(c.upload_time))

def reset_speedup():
    if not c.speedup_v:
        c.speedup = 1.0
    else:
        c.speedup_v = False
        c.after(500, reset_speedup)

def upload_data():
    if c.share:
        c.itemconfig(c.uploaded_text, text="hochladen...")
        c.session.post(c.basic_link+"uploader", {"pw": "lkunited", "message": c.id, "versionData": format_time(c.time)+"#*#"+c.lohn_akt.rstrip(" €")+"#*#"+c.status+"#*#"+format_money(c.lohn).rstrip(" €")+"#*#"+str(c.upload_time)})
        c.itemconfig(c.uploaded_text, text="erfolgreich hochgeladen")
        c.after(700, rm_upload_text)
        c.after(1000*c.upload_time, upload_data)
    else:
        c.after(1000, upload_data)

def rm_upload_text():
    c.itemconfig(c.uploaded_text, text="")

def update_ping(recall = True):
    if c.ping:
        c.server_ping = str(round(round(ping3.ping("lkunited.pythonanywhere.com"), ndigits=3)*1000))
        c.itemconfig(c.server_text, text=c.server_ping)
    else:
        c.itemconfig(c.server_text, text="OFF")
    if recall:
        c.after(90000, update_ping)

def update_ping_manual():
    update_ping(False)

def disable_ping_():
    c.ping = reverse(c.ping)
    update_ping_manual()

def show_new_():
    for i in c.new:
        i.config(background="yellow" if not c.show_new else "light blue")
    c.show_new = reverse(c.show_new)

def add():
    art_ = ["Stunden", "Minuten", "Sekunden", "Zehntelsekunden"]
    add_ = []
    for i in range(4):
        add_.append(int(py.prompt(f"Wie viele {art_[i]} wollen Sie hinzufügen?", "Zeit hinzufügen", "00" if i != 3 else "0")))
    for i in range(len(c.time)):
        c.time[i] = c.time[i] + add_[i]
    unit_ = [0, 60, 60, 10]
    for i in [3, 2, 1]:
        while c.time[i] > unit_[i]:
            c.time[i] = c.time[i] - unit_[i]
            c.time[i-1] = c.time[i-1] + 1

def presave(loadDef: bool = False):
    global c
    if not loadDef:
        loadsave = py.confirm("Wollen Sie speichern oder laden?", "Zwischenspeicherung", buttons=("Speichern", "Laden", "Abbrechen"))
    else:
        loadsave = "Laden"
    match loadsave:
        case "Speichern":
            if not c.paused:
                pause_play()
            file = asksaveasfilename(title="Namen und Verzeichnis wählen", filetypes=[("LK Rechnungen Speicherstand Dateien", "*.lkrs")])
            file += ".lkrs" if not file.endswith(".lkrs") else ""
            with open(file, "w", encoding="utf-8") as f:
                for i in c.time+[c.kunde, c.name, c.lohn, c.paused, c.share, c.id, c.upload_time, c.speedup]:
                    f.write(str(i)+"#**#")
                f.write(str(c.ping))
                if getattr(c, "protocol_enabled", False):
                    f.write("#**#PROTOCOL#**#")
                    f.write(str(c.protocol_enabled)+"#**#")
                    f.write(c.protocol_last_purpose+"#**#")
                    f.write("|".join(c.protocol))
                f.write("#**#TOOLTIP#**#")
                f.write(str(ToolTip.active))
            py.alert("Aktuellen Stand gespeichert.\nRechnungen beenden...", "Gespeichert")
            c.status = "zwischengespeichert"
            upload_data()
            quit(code="save_exit")
        case "Laden":
            share_def = c.share
            file = askopenfilename(title="Speicherstand wählen", filetypes=[("LK Rechnungen Speicherstand Dateien", "*.lkrs")])
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
            tooltip_state = True
            if "#**#TOOLTIP#**#" in content:
                main, tooltip_part = content.split("#**#TOOLTIP#**#", 1)
                tooltip_state = tooltip_part.strip().startswith("True")
            else:
                main = content
            if "#**#PROTOCOL#**#" in main:
                main, proto = main.split("#**#PROTOCOL#**#", 1)
                content_ = main.split("#**#")
                proto_ = proto.split("#**#")
                c.protocol_enabled = proto_[0] == "True"
                c.protocol_last_purpose = proto_[1]
                c.protocol = [entry.replace(" | Zweck: ", "\nZweck: ") for entry in proto_[2].split("|")] if proto_[2] else []
            else:
                content_ = main.split("#**#")
                c.protocol_enabled = False
                c.protocol_last_purpose = ""
                c.protocol = []
            if c.protocol_enabled:
                c.protocol_logged_start = False
            a = []
            type_ = ["int"]*4+["str"]*2+["float"]+["x_extra"]*2+["str", "int", "float", "x_extra"]
            for i in range(len(content_)):
                if type_[i] != "x_extra":
                    a.append(eval(type_[i]+"('"+content_[i]+"')"))
                else:
                    a.append(content_[i] == "True")
            c.time = a[0:4]; c.kunde = a[4]; c.name = a[5]; c.lohn = a[6]; c.paused = a[7]; c.share = a[8]
            c.id = a[9]; c.upload_time = a[10]; c.speedup = a[11]; c.ping = a[12]
            c.basic_link = "https://lkunited.pythonanywhere.com/Rechnungen/"
            c.link = c.basic_link + "view?id=" + c.id
            ToolTip.set_active(tooltip_state)
            if c.share != share_def:
                if c.share:
                    share()
                else:
                    unshare()
            c.itemconfig(c.stundenlohn_text, text="à "+format_money(c.lohn)+" pro Stunde entspricht das:")
            window.update()
            py.alert("Speicherstand erfolgreich geladen!", "Laden erfolgreich")
            update_protocol_window()
        case _:
            pass

def format_time(time_: list = [0, 0, 0, 0]):
    time2 = time_.copy()
    for i in range(3):
        if len(str(time2[i])) < 2:
            time2[i] = "0"+str(time2[i])
    return str(time2).rstrip("]").lstrip("[").replace(", ", " : ").replace("'", "")

def format_money(money):
    return str(money)+"0 €" if len(str(money).split(".")[-1]) < 2 else str(money)+" €"

def open_protocol_window():
    global protocol_window
    if 'protocol_window' in globals() and protocol_window and protocol_window.winfo_exists():
        protocol_window.lift()
        return
    protocol_window = Toplevel(window)
    protocol_window.title("Protokoll")
    protocol_window.geometry("400x220")
    protocol_window.resizable(False, False)
    protocol_window.configure(bg="light blue")
    Label(protocol_window, text="Protokoll (letzte 10 Einträge):", font=("Helvetica", 9, "bold"), bg="light blue").pack(anchor="w", padx=10, pady=(10,0))
    txt = Text(protocol_window, width=54, height=8, font=("Courier", 8), state="normal", bg="white", relief="solid", bd=1)
    txt.pack(padx=10, pady=5)
    txt.insert(END, "\n".join(c.protocol[-10:]) if c.protocol else "(Noch keine Einträge)")
    txt.config(state="disabled")
    ToolTip(txt, "Hier sehen Sie die letzten 10 Protokolleinträge (Start/Stop und Zweck).")
    protocol_window.protocol("WM_DELETE_WINDOW", protocol_window.destroy)

def create_button(share_: bool = True):
    if share_:
        c.open_link_b = Button(master=window, command=open_link, text="🌐", background="light blue", relief="ridge")
        ToolTip(c.open_link_b, "Link im Browser öffnen")
        c.copy_link_b = Button(master=window, command=copy_link, text="📋", background="light blue", relief="ridge")
        ToolTip(c.copy_link_b, "Link in Zwischenablage kopieren")
        c.speedup_b = Button(master=window, command=speedup, text="⏱️", background="light blue", relief="ridge")
        ToolTip(c.speedup_b, "Upload-Intervall beschleunigen")
        c.unshare_b = Button(master=window, command=unshare_agent, text="Teilen beenden", background="light blue", relief="ridge", activebackground="blue")
        ToolTip(c.unshare_b, "Teilen beenden")
    else:
        c.share_b = Button(master=window, command=share, text="Teilen", background="light blue", activebackground="cyan", relief="ridge", height=2, width=24)
        ToolTip(c.share_b, "Rechnung teilen")

def display_button(share_: bool = True):
    if share_:
        c.create_window(100, 325, window=c.copy_link_b)
        c.create_window(50, 325, window=c.open_link_b)
        c.create_window(350, 325, window=c.speedup_b)
        c.create_window(200, 385, window=c.unshare_b)
    else:
        c.create_window(200, 345, window=c.share_b)

# --- Fenster, Canvas, statische UI-Elemente ---
window = Tk()
window.title("Rechnungen")
window.resizable(False, False)
window.iconbitmap("./programdata/rechnungen/rechnung.ico")
c = Canvas(window, width=400, height=420)
c.configure(bg="light blue")
c.pack()

# Canvas-Elemente
c.time_text = c.create_text(200, 100, fill="black", font=("Helvetica", "30", "bold"))
c.lohn_text = c.create_text(200, 190, fill="black", font=("Helvetica", "30", "bold"))
c.link_text = c.create_text(200, 350, fill="black", font=("Helvetica, 6"))
c.id_text = c.create_text(200, 335, fill="black", font=("Helvetica", "10", "bold"))
c.descr_text = c.create_text(200, 315, fill="black", font=("Helvetica", "7"))
c.uptime_text2 = c.create_text(299, 318, fill="black", font=("Helvetica", "6"))
c.uptime_text = c.create_text(300, 332, fill="black", font=("Helvetica", "8"))
c.upload_time_text = c.create_text(307, 332, fill="black", font=("Helvetica", "9", "bold"))
c.uploaded_text = c.create_text(200, 360, fill="black", font=("Helvetica, 6"))
c.server_text = c.create_text(68, 414, fill="black", font=("Helvetica", "6", "bold"))
c.name_text = c.create_text(200, 240, fill="black", text="", font=("Helvetica", "10"))
c.stundenlohn_text = c.create_text(200, 150, fill="black", text="", font=("Helvetica", "10"))
c.create_text(200, 25, fill="black", text="LK Rechnungen", font=("Verdana", "20", "bold"))
c.create_text(200, 60, fill="black", text="Arbeitszeit bisher:", font=("Helvetica", "10"))
c.create_text(200, 415, fill="black", text="Copyright Leander Kafemann 2024-2025", font=("Helvetica", "5"))
c.create_text(340, 415, fill="black", text="App-Version:", font=("Helvetica", "5"))
c.create_text(53, 415, fill="black", text="Server-Ping:"+15*" "+"ms", font=("Helvetica", "5"))
c.create_text(380, 414, fill="black", text="2.0.0", font=("Helvetica", "6", "bold"))

# --- Initialisierung: Kunden, Lohn, Name etc. ---
try:
    with open("./programdata/rechnungen/kunden.txt", "r", encoding="utf-8") as f:
        c.kunden = f.read().split("#*#")
except:
    with open("./programdata/rechnungen/kunden.txt", "x", encoding="utf-8") as f:
        f.write("Leander Kafemann")
    c.kunden = ["Leander Kafemann"]
    with open("./programdata/rechnungen/Leander Kafemann.txt", "x", encoding="utf-8") as f:
        f.write("10.00#*#??")
c.kunde = ""; c.skipintro = False
while c.kunde not in c.kunden:
    c.kunde = py.confirm("Kunden auswählen", "Kunde", buttons=c.kunden.copy()+["Neuen Kunden erstellen", "Kunden entfernen", "Speicherstand laden"])
    if c.kunde == "Neuen Kunden erstellen":
        c.kunde = py.prompt("Namen des Kunden eingeben:", "Neuer Kunde")
        c.kunden.append(c.kunde)
        with open("./programdata/rechnungen/"+c.kunde+".txt", "x", encoding="utf-8") as f:
           f.write("10.00#*#??")
    elif c.kunde == "Kunden entfernen":
        c.kunde = py.confirm("Welchen Kunden wollen Sie löschen?", "Kunden entfernen", buttons=c.kunden)
        c.kunden.remove(c.kunde)
        os.remove("./programdata/rechnungen/"+c.kunde+".txt")
        c.kunde = ""
    elif c.kunde == "Speicherstand laden":
        c.kunde = c.kunden[0]; c.skipintro = True
with open("./programdata/rechnungen/kunden.txt", "w", encoding="utf-8") as f:
    for i in range(len(c.kunden)-1):
        f.write(c.kunden[i]+"#*#")
    f.write(c.kunden[-1])

with open("./programdata/rechnungen/"+c.kunde+".txt", "r", encoding="utf-8") as f:
    k_data = f.read().split("#*#")
if not c.skipintro:
    c.lohn = float(py.prompt("Stundenlohn in € eingeben:", "Initialisierung", k_data[0]))
    c.name = py.prompt("Namenskürzel Ihrer Institution eingeben:", "Initialisierung", k_data[1])
    if c.name in ["LK-Software", "LK Software"]:
        c.name = "LK Software Foundation"
    with open("./programdata/rechnungen/"+c.kunde+".txt", "w", encoding="utf-8") as f:
        f.write(str(c.lohn)+"#*#"+c.name)
else:
    c.lohn = 0.00
    c.name = "LK-INTRO-SKIP-AUTOFILL"

c.paused = True
c.status = "pausiert"
c.share = False
c.time = [0, 0, 0, 0]
c.lohn_akt = 0.0
c.id = str(random.randint(10**11, 10**12-1))
c.basic_link = "https://lkunited.pythonanywhere.com/Rechnungen/"
c.link = c.basic_link + "view?id=" + c.id
c.upload_time = 7
c.server_ping = "100"
c.speedup = 1.0
c.speedup_v = False
c.ping = False
c.show_new = False

c.itemconfig(c.name_text, text="an "+c.name)
c.itemconfig(c.stundenlohn_text, text="à "+format_money(c.lohn)+" pro Stunde entspricht das:")

# Protokoll initialisieren
init_protocol()
if not c.skipintro:
    ask_protocol_activation()

# --- Buttons und dynamische Buttons ---
c.play_pause = Button(master=window, command=pause_play, text="⏯️", background="light blue", activebackground="light green", relief="ridge")
ToolTip(c.play_pause, "Timer starten/pausieren")
create_button(False)
c.create_window(200, 280, window=c.play_pause)
display_button(False)

c.downloadB = Button(master=window, command=export_agent, text="🡇", background="light blue", activebackground="blue", relief="ridge")
ToolTip(c.downloadB, "Rechnung exportieren")
c.create_window(120, 280, window=c.downloadB, width=33)
stopB = Button(master=window, command=stop, text="⏹", background="light blue", activebackground="red", relief="ridge")
ToolTip(stopB, "Rechnung ohne Speichern beenden")
c.create_window(280, 280, window=stopB)
c.addTimeB = Button(master=window, command=add, text="➕", background="light blue", activebackground="green", relief="ridge")
ToolTip(c.addTimeB, "Zeit manuell hinzufügen")
c.create_window(240, 280, window=c.addTimeB)
c.presaveB = Button(master=window, command=presave, text="💾", background="light blue", activebackground="green", relief="ridge")
ToolTip(c.presaveB, "Speichern/Laden")
c.create_window(160, 280, window=c.presaveB)

update_pingB = Button(master=window, command=update_ping_manual, text="⟳", background="light blue", activebackground="light blue",relief="flat", width=1, height=1, font=("Helvetica", 8))
ToolTip(update_pingB, "Ping manuell aktualisieren")
c.create_window(105, 413, width=13, height=13, window=update_pingB)
c.adminPing = Button(master=window, command=disable_ping_, text="🗲", background="light blue", activebackground="light blue", relief="flat", width=1, height=1, font=("Helvetica", 9))
ToolTip(c.adminPing, "Server-Ping aktivieren/deaktivieren")
c.create_window(117, 412, width=13, height=19, window=c.adminPing)
c.whatsNew = Button(master=window, command=show_new_, text="ⓘ", background="light blue", activebackground="light blue", relief="flat", width=1, height=1, font=("Helvetica", 7))
ToolTip(c.whatsNew, "Was ist neu?")
c.create_window(306, 413, width=13, height=19, window=c.whatsNew)

# Protokoll-Button neben der Überschrift (rechts)
protocol_btn = Button(window, text="📋", width=2, height=1, relief="flat", bg="light blue", command=open_protocol_window, font=("Helvetica", 12))
protocol_btn.place(x=350, y=10, width=30, height=30)
ToolTip(protocol_btn, "Protokoll anzeigen")

# Tooltip-Button (💡) immer relief="flat"
def toggle_tooltips():
    ToolTip.set_active(not ToolTip.active)
tooltip_btn = Button(window, text="💡", width=2, height=2, relief="flat", bg="light blue", command=toggle_tooltips, font=("Helvetica", 9))
tooltip_btn.place(x=280, y=404, width=19, height=19)
ToolTip(tooltip_btn, "Tooltips für Hilfetexte aktivieren/deaktivieren", always_show=True)

c.new = [tooltip_btn, protocol_btn, c.play_pause, c.downloadB]

if c.skipintro:
    presave(loadDef = True)

c.after(100, update_time)
c.after(100, update_lohn)
c.after(1, update_ping)

c.session = requests.Session()
threading.Thread(target=upload_data).start()

window.mainloop()