
---

## 2026-10-16 - AOSP 16 BUILD VOLTOOID EN FACTORY ZIP GELEVERD

### Resultaat
- **Build succesvol**: `#### build completed successfully ####` (laatste fase 16:12)
- **Images**: system.img (940MB sparse), system_ext.img (214MB, met stay4s_agentd), product.img (313MB)
- **Factory zip**: `K:\stay4\stay4os_tegu-bp41_factory.zip` (3.025 GB, zip -0 store)
- **SHA256**: `5921a9dbd9bb1401a44b23bb6c09e90bce3e3f68bc50209ad2a158c907878d65`
- Flash instructies: `K:\stay4\FLASH_INSTRUCTIONS_STAY4OS_TEGU.md`

### Kritieke fixes deze sessie (chronologisch)
1. **kotlinx_serialization_core kotlinc failure** (16% blokkade): `kotlin_lang_version: "2"` toegevoegd aan beide modules in `external/kotlinx.serialization/Android.bp`. Root cause: _r1-tag snapshot (25Q2) gebruikt `kotlin.uuid.Uuid` (Kotlin 2.x API) maar AOSP defaulteert naar `-language-version 1.9` (build/soong/java/base.go:1352).
2. **FUNDAMENTELE RELEASE-CONFIG MISMATCH OPGELOST**: lunch stond op `ap4a` terwijl de tree **bp2a** is (BUILD_ID=BP2A). ap4a mist 37 platform flags. Overgeschakeld naar `stay4os_tegu-bp2a-userdebug` -> PLATFORM_VERSION werd correct 16 (was 15). Dit loste tevens op:
   - aconfig FeatureFlagsImpl DeviceConfig-fouten (bp2a zet RELEASE_ACONFIG_NEW_EXPORTED=true + RELEASE_READ_FROM_NEW_STORAGE=true -> nieuwe storage template zonder DeviceConfig-imports)
   - FederatedCompute Java 21 pattern-switch fout (bp2a zet RELEASE_TARGET_JAVA_21=true)
3. **apexd microdroid header**: `apex_file_repository.cpp` include `<microdroid/metadata.h>` (weg met Virtualization) -> block-device payload-scan vervangen door early return (dood pad zonder VM's).
4. **stay4s_agentd was een ELF binary, geen source** (51.752 bytes ARM64 PIE): Android.bp omgezet van `cc_binary` naar `cc_prebuilt_binary` + `.cpp`->`.bin` + `shared_libs: [liblog, libcutils]` (DT_NEEDED check) + `strip: none`.
5. **AppSearch AVF-verwijzingen**: `IsolatedStorageService.java` (APK) disabled + manifest-service weggehaald; `service-appsearch` kreeg stub.
6. **`framework-virtualization-stub` java_library** aangemaakt in `device/google/tegu/stubs/` met echte classes: `VirtualMachine`, `VirtualMachineManager` (CAPABILITY_*), `VirtualizationFrameworkInitializer` (no-op registerServiceWrappers). Gewired in `framework-minus-apex-defaults` (SystemServiceRegistry), `service-appsearch-defaults`, en `Settings-core` libs.
7. **RecoverySystemService secretkeeper**: ISecretkeeper AIDL (verwijderde HAL) gebruikt -> deleteSecrets() blok vervangen door skip met commentaar (KeyStore-wipe blijft intact via AndroidKeyStoreMaintenance).
8. **StorageManagerService mmd**: `mmdEnabled() && MmdProperties...` conditie -> `false && false` (klassieke zram else-tak altijd actief).
9. **SystemUI motion test DSL**: `PlatformMotionTestingComposeValues` stub was leeg maar SystemUI-productiecode gebruikt `motionTestValues { x exportAs key }` -> echte Kotlin stub geschreven (`MotionTestValueKey<T>`, `MotionTestValues.alpha`, `MotionTestValuesScope.exportAs` infix, `Modifier.motionTestValues` no-op) met `androidx.compose.ui_ui` static_lib, host-varianten verwijderd (compose is device-only).

### Finale build-configuratie
- Lunch: `stay4os_tegu-bp2a-userdebug` (AndroidProducts.mk + run_build.sh aangepast)
- Env: SKIP_ABI_CHECKS=true, ACONFIG_CONTAINER=system, RELEASE_ACONFIG_FLAG_DEFAULT_PERMISSION=READ_ONLY, RELEASE_BUILD_FLAGS="-s"
- WITH_DEXPREOPT=false, PRODUCT_OTA_ENFORCE_VINTF_KERNEL_REQUIREMENTS=false
- Vast.ai instance 56108303 (192 vCPU, 503GB RAM, $0.55/hr) - STILL RUNNING

### Openstaand
- Fysieke flash + smoke test op Pixel 9a (stock BP41 actief, bootloader unlocked)
- Vast.ai instance kan stopgezet na bevestiging dat zip compleet is (done: zip op K:\stay4\, hash geverifieerd)
- OpenCode deliverables blijven uitgesteld (gateway_v3.py, nexus_plugins_v2.py, voice_server_v2.py, consciousness_protocol.py, video.stay4s.com tunnel)
