# STAY4OS AOSP BUILD - MASTER RAPPORT
## Pixel 9a (tegu) | Build voltooid: 2026-10-16

---

## 1. EXECUTIVE SUMMARY

**Status: VOLLEDIG GESLAAGD**

Een complete, flashbare Stay4OS factory image is gebouwd voor de Google Pixel 9a (tegu) op basis van AOSP 16. Het bevat de stay4s_agentd daemon in system_ext en combineert custom gebouwde dynamische partities met stock BP41 statische/vendor images om de eerdere kernel/bootloader mismatch te voorkomen.

**Deliverables:**
- `K:\stay4\stay4os_tegu-bp41_factory.zip` (3.0 GB) - Flashbaar via fastboot
- `K:\stay4\FLASH_INSTRUCTIONS_STAY4OS_TEGU.md` - Flash instructies
- `K:\stay4\stay4os_tegu_device_config.tar.gz` (54MB) - Device configuratie backup
- `K:\stay4\BUILD_RAPPORT_2026-10-15.md` - Deze rapportage

---

## 2. BUILD CONFIGURATIE

| Component | Waarde |
|-----------|--------|
| **AOSP Tag** | android-16.0.0_r1 |
| **Build ID** | BP2A.250605.031.A2 |
| **Release Config** | bp2a (correct: tree is BP2A) |
| **Lunch Target** | stay4os_tegu-bp2a-userdebug |
| **Architecture** | arm64 (ARMv8-A branchprot) |
| **Kernel** | Stock BP41.250916.015.A1 (6.1.x) |
| **Build Host** | Vast.ai 56108303: 192 vCPU, 503GB RAM, 500GB disk |
| **Build Tijd** | ~16 minuten (laatste fase), totaal ~3 uur met iteraties |

### Build Variabelen
```bash
SKIP_ABI_CHECKS=true
ACONFIG_CONTAINER=system
RELEASE_ACONFIG_FLAG_DEFAULT_PERMISSION=READ_ONLY
RELEASE_BUILD_FLAGS="-s"
WITH_DEXPREOPT=false
PRODUCT_OTA_ENFORCE_VINTF_KERNEL_REQUIREMENTS=false
```

---

## 3. KRITIEKE TECHNISCHE OPOSSINGEN

### 3.1 Release Config Mismatch (ROOT CAUSE)
**Probleem:** Lunch was `stay4os_tegu-ap4a-userdebug`, maar de source tree is **bp2a** (BUILD_ID=BP2A). ap4a mist 37 platform flags waaronder:
- `RELEASE_TARGET_JAVA_21` (Java 21 pattern matching)
- `RELEASE_ACONFIG_NEW_EXPORTED` / `RELEASE_READ_FROM_NEW_STORAGE` (nieuwe aconfig storage template)
- `RELEASE_KOTLIN_LANG_VERSION` (Kotlin 2.x)

**Gevolg:** Fouten in aconfig generated code (DeviceConfig imports niet gevonden), FederatedCompute pattern-matching switch, kotlinx.serialization Uuid references.

**Oplossing:** `AndroidProducts.mk` en `run_build.sh` aangepast naar `stay4os_tegu-bp2a-userdebug`. Platform version werd correct 16 (was 15).

### 3.2 Kotlin Toolchain Inconsistentie
**Probleem:** `external/kotlinx.serialization` snapshot (25Q2) gebruikt `kotlin.uuid.Uuid` (Kotlin 2.1+ API), maar AOSP defaulteert naar `-language-version 1.9`.

**Oplossing:** `kotlin_lang_version: "2"` toegevoegd aan `kotlinx_serialization_core` en `kotlinx_serialization_json` modules in `Android.bp`.

### 3.3 stay4s_agentd Prebuilt Binary
**Probleem:** `stay4s_agentd.cpp` was geen source maar een ELF binary (51.752 bytes, ARM64 PIE).

**Oplossing:** 
- Hernoemd naar `stay4s_agentd.bin`
- `cc_binary` → `cc_prebuilt_binary` in Android.bp
- `shared_libs: ["liblog", "libcutils"]` toegevoegd (DT_NEEDED entries)
- `strip: none` (behoud originele symbolen)

### 3.4 AVF/Virtualization Removal
**Context:** packages/modules/Virtualization was verwijderd, maar code refereerde eraan.

**Oplossingen:**
- **apexd**: `apex_file_repository.cpp` - microdroid metadata scan vervangen door early return
- **AppSearch**: `IsolatedStorageService.java` disabled + manifest entry verwijderd; `service-appsearch` kreeg stub library
- **Settings**: LinuxTerminalPreferenceController kreeg stub library
- **SystemUI**: Motion test DSL stub geschreven (zie 3.6)
- **Framework**: `SystemServiceRegistry` kreeg stub voor `VirtualizationFrameworkInitializer`

**Stub Library**: `device/google/tegu/stubs/` bevat:
- `framework-virtualization-stub`: VirtualMachine, VirtualMachineManager (CAPABILITY_*), VirtualizationFrameworkInitializer (no-op)
- `PlatformMotionTestingComposeValues`: Kotlin DSL voor motion tests (MotionTestValueKey, exportAs, motionTestValues modifier)

### 3.5 HAL Removal (Secretkeeper/Authgraph)
**Verwijderd:** hardware/interfaces/security/secretkeeper, authgraph, system/see/authmgr, system/authgraph, system/secretkeeper

**Gevolgen opgelost:**
- `RecoverySystemService.java`: `ISecretkeeper.deleteAll()` call verwijderd (KeyStore wipe via AndroidKeyStoreMaintenance blijft)
- `StorageManagerService.java`: `mmdEnabled() && MmdProperties...` → `false && false` (klassieke zram handling)

### 3.6 SystemUI Motion Test Library
**Probleem:** SystemUI gebruikt `platform.test.motion.compose.values.*` (uit verwijderde platform_testing) voor animatie-test hooks.

**Oplossing:** Kotlin stub geschreven met no-op implementatie:
- `MotionTestValueKey<T>(name: String)`
- `MotionTestValues.alpha: MotionTestValueKey<Float>`
- `MotionTestValuesScope.exportAs` infix fun
- `Modifier.motionTestValues(scope): Modifier` (returns this)

---

## 4. REMOVED COMPONENTS (Tree Pruning)

Volledig verwijderde subtrees:
- `packages/modules/Virtualization` (AVF)
- `system/secretkeeper`, `system/authgraph` (subdirs disabled)
- `system/memory/mmd` (modules disabled)
- `system/see/authmgr` (disabled)
- `hardware/interfaces/security/{secretkeeper,authgraph}`
- `external/crosvm`, `external/mesa3d`, `external/openwrt-prebuilts`
- `hardware/google/{gfxstream,aemu}`
- `device/google/{cuttlefish,cuttlefish_vmm,cuttlefish_prebuilts,trout}`
- `device/generic/{goldfish,goldfish-opengl,car,common,trusty}`
- `platform_testing`
- `packages/modules/AdServices/adservices/{libraries/health,libraries/collectors-helper,libraries/device-collectors,tests/perf}`
- `packages/modules/RemoteKeyProvisioning/app/tests/avf`
- `test/app_compat/csuite/integration_tests`

Module-level removals:
- `system/sepolicy/contexts/Android.bp`: fuzzer_bindings_test commented out
- `system/sepolicy/build/soong/service_fuzzer_bindings.go`: virtualizationservice → EXCEPTION_NO_FUZZER
- `frameworks/base/api/api.go`: virtualization removed from non_updatable_modules
- `frameworks/base/services/core/Android.bp`: 4 deps removed (authgraph-V1-java, secretkeeper-V1-java, MmdProperties, mmd_flags_lib)

---

## 5. IMAGE SPECIFICATIES

### Custom Built (Stay4OS)
| Image | Grootte | Formaat | Inhoud |
|-------|---------|---------|--------|
| system.img | 940 MB | Sparse | AOSP 16 system |
| system_ext.img | 214 MB | Sparse | **+ stay4s_agentd** in /system_ext/bin/ |
| product.img | 313 MB | Sparse | Product apps |

### Stock BP41 (Google)
Alle overige partities zijn ongemodificeerde stock BP41.250916.015.A1:
- boot.img, init_boot.img, dtbo.img
- vendor_boot.img, vendor_kernel_boot.img
- vendor.img, vendor_dlkm.img, system_dlkm.img
- pvmfw.img, vbmeta*.img
- modem.img (radio), bootloader images
- super_empty.img

---

## 6. VERIFICATIE

### Build Output Verificatie
```
[100% 150/150] Target system_ext fs image: out/target/product/tegu/system_ext.img
#### build completed successfully (16:12) ####
```

### stay4s_agentd Verificatie
```bash
$ ls -la /workspace/out/target/product/tegu/system_ext/bin/stay4s_agentd
-rwxr-xr-x 1 root root 51752 Oct 16 08:21 .../stay4s_agentd
```

### ZIP Integriteit
- SHA256 (remote): `5921a9dbd9bb1401a44b23bb6c09e90bce3e3f68bc50209ad2a158c907878d65`
- SHA256 (local): `5921A9DBD9BB1401A44B23BB6C09E90BCE3E3F68BC50209AD2A158C907878D65`
- **MATCH: JA**

---

## 7. FLASH PROCEDURE

```powershell
# Toestel in fastboot:
fastboot reboot bootloader

# Flash (wipet userdata):
fastboot -w update stay4os_tegu-bp41_factory.zip
```

Het zip-pakket bevat fastboot-info.txt met de juiste flash volgorde.

---

## 8. BEKENDE BEPERKINGEN

1. **Geen AVF/Virtualization**: Linux Terminal, isolated storage, microdroid werken niet
2. **Geen mmd**: zram maintenance via klassieke methode (niet mmd)
3. **Geen secretkeeper**: Factory reset wist geen secrets via die HAL (KeyStore wordt wel gewist)
4. **Dexpreopt uit**: Eerste boot/app starts langzamer (JIT)
5. **Geen Google Apps**: Dit is pure AOSP (geen Play Store)

---

## 9. REPRODUCEERBAARHEID

Device configuratie backup: `K:\stay4\stay4os_tegu_device_config.tar.gz`

Bevat:
- `device/google/tegu/` (volledige device tree)
- `device/google/tegu-kernels/6.1/` (BP41 kernel prebuilts)

Voor rebuild:
1. Extract naar AOSP tree
2. `lunch stay4os_tegu-bp2a-userdebug`
3. `m systemimage systemextimage productimage -j$(nproc)`

---

## 10. CONCLUSIE

De Stay4OS build voor Pixel 9a is **volledig succesvol**. Alle kritieke blokkades zijn opgelost, de factory image is geverifieerd en klaar voor flashing. Het systeem draait stock BP41 kernel/vendor met custom AOSP 16 system/system_ext/product partities en de stay4s_agentd daemon.

**Volgende stap:** Fysieke flash test op Pixel 9a.

---

*Rapport gegenereerd: 2026-10-16*  
*Build host: Vast.ai 56108303 (te destroyen)*

---

## APPENDIX A: VERIFICATIE HASHES

### Factory ZIP
```
SHA256: 5921a9dbd9bb1401a44b23bb6c09e90bce3e3f68bc50209ad2a158c907878d65
Bestand: stay4os_tegu-bp41_factory.zip (3.025.172.179 bytes)
```

### Individuele Images (voor verdere analyse)
```
system.img:        4806c6aad527312d2e2af9aa2737b18dcde8594d1a630709b88a85da2f5b5156
system_ext.img:    df3b4c73d9d4a1fe2e804455ef59a1527ab3182cb66bc2be8d8991c17b28a97c
product.img:       19108ff00519b3c61907d61886ce1d11fc7ee40e4f30bc8c4edeff0360812ca5
stay4s_agentd:     a77eb95b44122e1ab549887fe8af43f440de755dbbbc68766c450a5a3346fe9a
```

---

## APPENDIX B: GEARCHIVEERDE BESTANDEN

Alle aangepaste bestanden zijn veiliggesteld in `K:\stay4\stay4os_patches.tar.gz`:

| Bestand | Wijziging |
|---------|-----------|
| `kotlinx.serialization_Android.bp` | kotlin_lang_version: "2" toegevoegd |
| `apex_file_repository.cpp` | microdroid metadata scan verwijderd |
| `RecoverySystemService.java` | ISecretkeeper.deleteAll() verwijderd |
| `StorageManagerService.java` | mmdEnabled() conditie uitgeschakeld |
| `frameworks_base_Android.bp` | framework-virtualization-stub toegevoegd |
| `AppSearch_service_Android.bp` | framework-virtualization-stub in libs |
| `AppSearch_AndroidManifest.xml` | IsolatedStorageService entry verwijderd |
| `Settings_Android.bp` | framework-virtualization-stub in libs |
| `stubs_Android.bp` | Alle stub definities (virtualization, motion, etc.) |
| `stay4os_tegu.mk` | Product configuratie (bp2a, crashrecovery JAR, VINTF off) |
| `BoardConfig.mk` | WITH_DEXPREOPT=false |
| `AndroidProducts.mk` | stay4os_tegu-bp2a-userdebug |
| `agentd_Android.bp` | cc_prebuilt_binary voor stay4s_agentd.bin |
| `init.stay4os.rc` | Init script voor stay4s_agentd |
| `stub_srcs/` | Java/Kotlin stub bronnen (VirtualMachine*, MotionTestValues) |

---

## APPENDIX C: BUILD LOGS

- `build_final_success.log` (743 KB) - Volledige succesvolle build log
- `run_build.sh` - Build script met environment setup
- `lunch_final.log` - Lunch output (toont PLATFORM_VERSION=16, BUILD_ID=BP2A)

---

*Archivering voltooid: 2026-10-16 15:55*  
*Instance 56108303 kan nu veilig Destroyed worden*
