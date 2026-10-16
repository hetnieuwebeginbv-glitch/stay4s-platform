# Stay4OS v1.0 - Pixel 9a (tegu)

## 🚀 Release Inhoud

| Map | Inhoud |
|-----|--------|
| `01_FACTORY_ZIP/` | Flashbare factory image (3.0 GB) |
| `02_RAPPORTEN/` | Technische documentatie |
| `03_BACKUPS/` | Device config + patches (voor rebuild) |
| `04_LOGS/` | Build logs en scripts |
| `05_FLASH/` | Flash instructies en stappenplan |

## ⚡ Snelstart

```powershell
# 1. Ga naar de juiste map
cd 01_FACTORY_ZIP

# 2. Flash
fastboot -w update stay4os_tegu-bp41_factory.zip
```

## 📱 Specificaties

| Eigenschap | Waarde |
|------------|--------|
| **Toestel** | Google Pixel 9a (tegu) |
| **Basis** | AOSP 16 (android-16.0.0_r1) |
| **Build ID** | BP2A.250605.031.A2 |
| **Kernel** | Stock BP41.250916.015.A1 |
| **Custom** | stay4s_agentd in /system_ext/bin/ |

## 📚 Documentatie

- `02_RAPPORTEN/STAY4OS_ULTIEME_MASTER_RAPPORT.md` - Volledige technische rapportage
- `05_FLASH/STAPPENPLAN_FLASH_VANAVOND.md` - Stap-voor-stap flash guide

## ⚠️ Waarschuwingen

- Eerste boot duurt 5-10 minuten (dexpreopt uit)
- Alles op telefoon wordt gewist bij flash
- Geen Google Apps (pure AOSP)
- Geen AVF/Virtualization features

## 🔐 Verificatie

SHA256: `5921a9dbd9bb1401a44b23bb6c09e90bce3e3f68bc50209ad2a158c907878d65`

---

*Build voltooid: 2026-10-16*
