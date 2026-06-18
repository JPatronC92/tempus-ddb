#!/usr/bin/env bash
# ============================================================================
# ⚠️  DEPRECATED — DO NOT USE
# ============================================================================
#
# This script is DEPRECATED and will be removed in a future release.
#
# It previously generated a Python SDK wrapper using raw C FFI (ctypes) to call
# Rust functions `record_decision_ffi` and `free_string_ffi`. Those FFI
# functions were never implemented in the Rust crate, making this script
# non-functional.
#
# The SUPPORTED integration path for Python is now PyO3 via maturin:
#
#   1. Install maturin:
#        pip install maturin
#
#   2. Build & install the Python module:
#        maturin develop --release
#
#   3. Use in Python:
#        from tempus_ddb import TempusDDB
#        ddb = TempusDDB(license_key="...", db_path="tempus_ddb.db", keyfile="keys.json")
#        result = ddb.record(payload='{"key":"value"}', rules='{"rule":1}')
#
# For JavaScript / WASM integration, build with:
#        wasm-pack build --target web
#
# ============================================================================

echo "❌ ERROR: build_sdk.sh is DEPRECATED."
echo ""
echo "This script referenced non-existent FFI functions (record_decision_ffi,"
echo "free_string_ffi) and is no longer supported."
echo ""
echo "Please use PyO3 via maturin for Python integration:"
echo "  pip install maturin"
echo "  maturin develop --release"
echo ""
echo "See the script header comments for full usage instructions."
exit 1
