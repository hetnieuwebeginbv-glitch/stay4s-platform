# ==============================================================================
# STAY4OS FLASH STAPPENPLAN - PIXEL 9A (tegu)
# Vanavond starten | Geschatte tijd: 30-45 minuten
# ==============================================================================

## VOORBEREIDING (10 minuten)

### Stap 1: Controleer benodigdheden
- [ ] Pixel 9a (tegu) - volledig opgeladen of aan de lader
- [ ] USB-C kabel (data-kabel, geen laad-only kabel)
- [ ] Windows PC met K:\stay4\ toegankelijk
- [ ] Internetverbinding (voor evt. downloads)

### Stap 2: Download en installeer Platform Tools
Als je nog geen fastboot hebt:
```powershell
# Download
Invoke-WebRequest -Uri "https://dl.google.com/android/repository/platform-tools-latest-windows.zip" -OutFile "$env:USERPROFILE\Downloads\platform-tools.zip"

# Uitpakken
Expand-Archive -Path "$env:USERPROFILE\Downloads\platform-tools.zip" -DestinationPath "C:\platform-tools"

# Toevoegen aan PATH (tijdelijk voor deze sessie)
$env:Path += ";C:\platform-tools"

# Verifieer
fastboot --version
```

### Stap 3: Controleer bestanden
```powershell
# Ga naar de map
cd K:\stay4\

# Controleer of alles er is
Get-ChildItem stay4os_tegu-bp41_factory.zip, FLASH_INSTRUCTIONS_STAY4OS_TEGU.md

# Verifieer hash (optioneel maar aanbevolen)
(Get-FileHash stay4os_tegu-bp41_factory.zip -Algorithm SHA256).Hash
# Moet zijn: 5921A9DBD9BB1401A44B23BB6C09E90BCE3E3F68BC50209AD2A158C907878D65
```

---

## BOOTLOADER ONTGRENDELING (5-10 minuten)

### Stap 4: OEM Unlocking aanzetten
1. Ga op de telefoon naar: **Instellingen > Over de telefoon**
2. Tik **7x op "Build-nummer"** (BP41.250916.015.A1) tot "Je bent nu ontwikkelaar"
3. Ga naar: **Instellingen > Systeem > Opties voor ontwikkelaars**
4. Zet **"OEM-ontgrendeling"** AAN (aanvinken)
5. Zet **"USB-foutopsporing"** AAN

### Stap 5: Fastboot modus
```powershell
# Sluit telefoon aan via USB
# Controleer verbinding
adb devices
# Moet tonen: [serienummer]    device

# Herstart naar fastboot
adb reboot bootloader
```

### Stap 6: Controleer fastboot
```powershell
fastboot devices
# Moet tonen: [serienummer]    fastboot
```

### Stap 7: Ontgrendel bootloader (ALLEEN ALS NOG GEBLOKKEERD)
```powershell
fastboot flashing unlock
```
- Op telefoon: Volume omhoog/omlaag om "UNLOCK" te selecteren, Power knop om te bevestigen
- **WAARSCHUWING:** Dit wist ALLES op de telefoon
- Telefoon herstart meerdere keren

---

## STAY4OS FLASHEN (10-15 minuten)

### Stap 8: Naar fastboot modus (na unlock)
Als telefoon is herstart:
```powershell
# Zet weer in fastboot
adb reboot bootloader
# OF: Volume omlaag + Power indrukken bij opstarten
```

### Stap 9: Flash de factory image
```powershell
# Ga naar de juiste map
cd K:\stay4\

# Start de flash
fastboot -w update stay4os_tegu-bp41_factory.zip
```

**Wat er gebeurt:**
1. `fastboot` flasht bootloader, radio, boot images
2. Telefoon herstart naar **fastbootd** (speciale modus)
3. Dynamische partities worden geflasht (system, system_ext, product, vendor)
4. `-w` wist userdata en metadata
5. Telefoon herstart automatisch

**Verwachte output:**
```
extracting android-info.txt (0 KB) to RAM...
extracting boot.img (64 MB) to disk... took 0.2s
...
archive does not contain 'vbmeta.img'
...
Rebooting into fastboot                            OKAY [  0.0s]
< waiting for any device >
...
Sending 'system' (940 MB)                        OKAY [ 25.0s]
Writing 'system'                                 OKAY [  5.0s]
...
Finished. Total time: 180.0s
```

### Stap 10: Eerste boot
- Telefoon start automatisch op na flash
- **Eerste boot duurt LANG (5-10 minuten)** door JIT (dexpreopt uit)
- Je ziet "Android" logo of Google logo
- Wacht geduldig

---

## VERIFICATIE (5 minuten)

### Stap 11: Controleer installatie
Na eerste boot, setup doorlopen (taal, wifi, etc.), dan:

```powershell
# Check build fingerprint
adb shell getprop ro.build.fingerprint
# Moet zijn: Stay4OS/stay4os_tegu/tegu:16/BP2A.250605.031.A2/...

# Check of stay4s_agentd er is
adb shell ls -la /system_ext/bin/stay4s_agentd
# Moet tonen: -rwxr-xr-x ... 51752 ... stay4s_agentd

# Check of daemon draait
adb shell ps -A | grep stay4s
# Moet tonen: stay4s_agentd process

# Check logs
adb logcat | grep -i stay4s
```

### Stap 12: Test functionaliteit
- [ ] Telefoon start volledig op
- [ ] Touchscreen werkt
- [ ] Wifi verbinding werkt
- [ ] stay4s_agentd draait (zie stap 11)

---

## PROBLEEMOPLOSSING

### Flash faalt met "not enough space"
- Dynamische partitie te klein? Controleer of je echt tegu hebt: `fastboot getvar product`

### Telefoon start niet op (bootloop)
- Stock BP41 flashen om te herstellen: https://developers.google.com/android/images#tegu
- Of: `fastboot -w update` opnieuw proberen

### "fastboot: error: Failed to identify current slot"
- Gebruik: `fastboot --set-active=a` of `fastboot --set-active=b`

### stay4s_agentd niet gevonden
- Controleer of zip correct is: `unzip -l stay4os_tegu-bp41_factory.zip | findstr system_ext`
- Controleer of image correct gebouwd is: `adb shell ls /system_ext/bin/`

---

## BELANGRIJKE INFORMATIE

### Wat werkt NIET (verwacht)
- Linux Terminal (AVF verwijderd)
- Google Play Store (pure AOSP)
- Sommige Pixel-specifieke features

### Wat werkt WEL
- Basis Android 16
- Telefoon, sms, wifi, bluetooth
- Camera (via stock vendor)
- stay4s_agentd daemon

### Contact
Bij problemen: check `K:\stay4\STAY4OS_ULTIEME_MASTER_RAPPORT.md` voor technische details.

---

## CHECKLIST VOOR VANAVOND

Print deze lijst en vink af:

- [ ] Platform tools geïnstalleerd
- [ ] OEM unlocking aan op telefoon
- [ ] USB debugging aan op telefoon
- [ ] Telefoon in fastboot modus
- [ ] Bootloader unlocked (indien nodig)
- [ ] `fastboot -w update stay4os_tegu-bp41_factory.zip` uitgevoerd
- [ ] Eerste boot voltooid (geduld!)
- [ ] Build fingerprint geverifieerd
- [ ] stay4s_agentd geverifieerd
- [ ] Alles werkt

---

**Geschatte totale tijd: 30-45 minuten**
**Moeilijkheidsgraad: Gemiddeld**
**Risico: Laag (stock BP41 recovery mogelijk)**

Succes! 🚀
