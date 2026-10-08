#!/bin/bash
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH
export TEMPORARY_DISABLE_PATH_RESTRICTIONS=true
export ALLOW_MISSING_DEPENDENCIES=true
export BUILD_BROKEN_MISSING_REQUIRED_MODULES=true

cd /workspace

# Fix missing files
mkdir -p system/core/trusty
touch system/core/trusty/trusty-storage.mk
mkdir -p hardware/google/pixel/lineage_health
touch hardware/google/pixel/lineage_health/device.mk

# Also fix any other missing lineage files
mkdir -p hardware/google/pixel/lineage_health
echo "LOCAL_PATH := \$(call my-dir)" > hardware/google/pixel/lineage_health/Android.mk
echo "include \$(CLEAR_VARS)" >> hardware/google/pixel/lineage_health/Android.mk

source build/envsetup.sh
make aidl -j$(nproc) 2>/dev/null || true
make android.hardware.common-V2-ndk-source -j$(nproc) 2>/dev/null || true

lunch aosp_tegu-bp2a-userdebug 2>&1 | tail -10

echo "=== BUILD START $(date) ==="
m bacon -j$(nproc) 2>&1 | tail -100
BUILD_EXIT=$?
echo "=== BUILD EXIT $BUILD_EXIT $(date) ==="

if ls out/target/product/tegu/*ota*.zip 2>/dev/null; then
    echo "=== OTA FOUND ==="
    ls -lh out/target/product/tegu/*ota*.zip
    cp out/target/product/tegu/*ota*.zip /workspace/stay4s_aosp_ota.zip
    echo "OTA at /workspace/stay4s_aosp_ota.zip"
else
    echo "=== NO OTA ==="
    ls out/target/product/tegu/*.zip 2>/dev/null || echo "No zips found"
fi