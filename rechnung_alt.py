import time
text = "------------------------------------------------------"
tag = input("letzter Tag?")
text += "\nRechung vom "+tag
zeit = input("Zeit?")
text += "\ngearbeitete Zeit: "+zeit+"h"
zl = zeit.split(":")
x = input("Stundenlohn?")
lohn = float(x) if x != "" else 1.50
stunden = str(round(float(int(zl[0])+int(zl[1])/60+int(zl[2])/3600+int(zl[3])/36000)*lohn, ndigits=2))
text += "\nà "+str(lohn)+"€/h \u2259 "+stunden+"€"
x = input("verbleibende Zahlungen(10%Zins)?")
verbl = str(round(float(x)*1.1, ndigits=2)) if x != "" else "0.0"
x = input("berechnete Pauschalen?")
pauschalen = x if x != "" else "0.0"
text += "\nberechnete Pauschalen: "+pauschalen+"€"
text += "\nverbleibende Zahlungen(10%Zins)?: "+verbl+"€"
text += "\nZu zahlen innerhalb von 5 Tagen."
gesamt = str(float(stunden)+float(verbl)+float(pauschalen))
text += "\nGesamtsumme: "+gesamt+"€"
ga = str(round(float(gesamt)*0.9995, ndigits=2))
text += "\nAn die Gartenkasse: "+ga+"€"
text += "\nAn LK-services .5%: "+str(round(float(gesamt)-float(ga), ndigits=2))+"€"
x = input("Namenskürzel")
name = x if x != "" else "LK"
text += "\ngezeichnet: "+name+" (Umsatzsteuerbefreit)"
text += "\n------------------------------------------------------"
print(text)
with open("./rechnung"+tag+name+".txt", "w", encoding="utf-8") as f:
    f.write(text)
time.sleep(30)
