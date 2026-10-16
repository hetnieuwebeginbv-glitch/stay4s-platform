#!/bin/bash
cd /workspace
export SKIP_ABI_CHECKS=true
export ACONFIG_CONTAINER=system
export RELEASE_ACONFIG_FLAG_DEFAULT_PERMISSION=READ_ONLY
export RELEASE_BUILD_FLAGS="-s"
source build/envsetup.sh > /tmp/envsetup.log 2>&1
lunch stay4os_tegu-bp2a-userdebug > /tmp/lunch.log 2>&1
echo "=== LUNCH OK ==="
date
m systemimage systemextimage productimage -j192 2>&1 | tee /workspace/build.log
echo "=== BUILD EXIT: $? ==="
date
