# Stay4OS voor Pixel 9a (tegu) - Flash Instructies

## Pakket
- **Bestand**: `stay4os_tegu-bp41_factory.zip` (3.025.172.179 bytes)
- **SHA256**: `5921a9dbd9bb1401a44b23bb6c09e90bce3e3f68bc50209ad2a158c907878d65`
- **Basis**: AOSP 16 (android-16.0.0_r1, BUILD_ID BP2A.250605.031.A2), release config **bp2a**
- **Hybride opbouw**: stock BP41.250916.015.A1 statische/vendor partities + custom gebouwde dynamische partities (system, system_ext, product)
- **Custom component**: `stay4s_agentd` (prebuilt ARM64 ELF) in `/system_ext/bin/`, gestart via `init.stay4os.rc`

## Voorwaarden
1. Pixel 9a met **ontgrendelde bootloader**
2. Toestel draait reeds stock BP41.250916.015.A1 (bootloader tegu-16.4-14097580, radio g5300t-250909). Zo niet: flash eerst de stock BP41 factory image.
3. Recent platform-tools (fastboot >= 33.0.1)

## Flash procedure
```powershell
# Toestel in fastboot-modus:
fastboot reboot bootloader   # of: Volume Down + Power bij boot

# Flash de volledige image-set (wipet userdata!):
fastboot -w update stay4os_tegu-bp41_factory.zip
```

Het zip-pakket bevat fastboot-info.txt die de volgorde stuurt:
boot, init_boot, dtbo, vendor_kernel_boot, pvmfw, vendor_boot, vbmeta,
reboot naar fastbootd, update-super, system, system_dlkm, system_ext,
product, vendor, vendor_dlkm, system_other + wipe userdata/metadata.

## Verificatie na boot
```powershell
adb shell getprop ro.build.fingerprint   # Stay4OS/stay4os_tegu/tegu:16/BP2A.250605.031.A2/...
adb shell ls -la /system_ext/bin/stay4s_agentd
adb shell ps -A | grep stay4s            # daemon zou moeten draaien
adb logcat | grep -i stay4s
```

## Belangrijke notities
- **Kernel/bootloader mismatch van de vorige poging is verholpen**: we gebruiken de ongemodificeerde stock BP41 boot/vendor images; alleen de dynamische partities zijn custom.
- VINTF kernel check is uitgeschakeld in de build (PRODUCT_OTA_ENFORCE_VINTF_KERNEL_REQUIREMENTS=false); runtime VINTF compatibiliteit met stock vendor is behouden via de stock vendor image.
- Dexpreopt is uitgeschakeld (eerste boot duurt langer; apps worden JIT gestart).
- AVF/Virtualization, mmd, authgraph/secretkeeper HALs zijn verwijderd; bijbehorende codepaden zijn gepatcht (AppSearch isolated storage, RecoverySystemService secretkeeper, StorageManagerService mmd, apexd payload-scan).
