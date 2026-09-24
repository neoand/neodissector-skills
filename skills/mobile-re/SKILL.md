---
name: mobile-re
description: Android and iOS reverse engineering with Frida 17.18 (Barebone, kernel-assisted), MobSF 4.5.3, apktool 3.x, jadx 1.5.x, and modern mobile RE workflows. Covers APK/IPA structure, DEX/Mach-O analysis, Smali assembly, Swift calling convention, Jailbroken iOS analysis, anti-Frida bypasses, and Frida Stalker v2 for mobile targets.
disable-model-invocation: true
risk: unknown
source: community
date_added: '2026-09-22'
---

# Mobile Reverse Engineering — Android & iOS (2025-2026)

Reverse engineering of mobile applications (Android APK/AAB + iOS IPA) for authorized security research, pentesting, malware analysis, and interoperability. Targets: Frida 17.18.0 (Barebone, LanguageServer, Stalker v2), MobSF 4.5.3, apktool 3.x, jadx 1.5.x, Objection [VERIFY], Corellium (requires Frida 17+).

## Use this skill when

- Analyzing Android APK or App Bundle (AAB) — Dalvik bytecode, Smali, native libraries (ARM64/ARMv7/x86)
- Analyzing iOS IPA — Mach-O universal binaries, Objective-C runtime, Swift calling convention, dyld shared cache
- Hooking live mobile processes with Frida 17 (Android barebone, iOS jailbroken)
- Static + dynamic mobile app pentesting (MobSF 4.5.3 workflow)
- Bypassing anti-Frida, anti-debug, anti-root, jailbreak detection, Play Integrity attestation
- RE of cross-platform frameworks (Flutter, React Native, Xamarin, Cordova)
- Recovering cryptographic keys, tokens, or API endpoints from mobile apps
- Auditing mobile app security for compliance (MASVS, OWASP MSTG)

## Do not use this skill when

- Reverse engineering proprietary apps without authorization (piracy, license bypass, IP theft)
- Building malware or evading security products maliciously
- Bypassing DRM or copy protection for unauthorized distribution
- Targeting devices without explicit written permission
- Static analysis of pure desktop binaries (use `reverse-engineer`)
- Firmware/IoT RE only (use `firmware-analyst`)
- Pure network protocol analysis (use `protocol-reverse-engineering`)

## Modern toolchain overview (Sep 2026)

| Tool | Latest verified | Best for | Notes |
|---|---|---|---|
| Frida | 17.18.0 (09 set 2026) | Dynamic instrumentation | Barebone (.kext macOS, .ko Linux), Stalker v2, LanguageServer LSP, TypeScript 7.0 |
| MobSF | 4.5.3 (21 set 2026) | Static + dynamic mobile analysis | Frida 17+ integration, Jailbroken iOS beta, apksigner 37.0.0, LIEF 0.17 |
| apktool | 3.x (2026) | APK/AAB decode + rebuild | Full support since MobSF 4.5.2 (10 ago 2026) |
| jadx | 1.5.x (2026) | DEX → Java decompiler | Replaced dex2jar as community standard |
| dex2jar | legacy | DEX → JAR (legacy) | Community migrated to jadx; use only for niche compatibility |
| Objection | 1.11 [VERIFY] | Runtime mobile exploration | Built on Frida; verify repo status before use |
| Corellium | requires Frida 17+ | Cloud iOS device farm | Breaking change in MobSF 4.4.1 (31 ago 2025) |
| apksigner | 37.0.0 (MobSF 4.5.2) | APK signature v1/v2/v3/v4 | Bundled with modern Android SDK build-tools |
| Capstone | 6.0.0-Alpha11 / 5.0.9 stable | Disassembly framework | ARM64 Thumb2 disassembly for native libs |
| LIEF | 0.17 (MobSF 4.5.3) | Binary parsing (PE/ELF/Mach-O) | Used by MobSF for static analysis |

## Android RE

### APK structure

```
app.apk (ZIP container)
├── AndroidManifest.xml          (binary AXML, decode via apktool)
├── classes.dex                  (classes2.dex, classes3.dex for multidex)
├── lib/{arm64-v8a,armeabi-v7a,x86_64,x86,riscv64}/   (native code)
├── assets/                       (Flutter snapshots, JS bundles)
├── resources.arsc               (compiled resources)
├── META-INF/{CERT.RSA,MANIFEST.MF,*.SF}                (v1 signature)
└── apk-signing-key-id          (v3.1/v4 signing block identifier)
```

Quick inspection: `unzip -l app.apk`, `unzip -p app.apk AndroidManifest.xml | xxd | head`, `sha256sum app.apk`.

### AndroidManifest.xml analysis

Binary AXML (not text XML). Always decode first:
```bash
apktool d app.apk -o decoded/ -f                # Full decode
aapt2 dump xmltree app.apk --file AndroidManifest.xml  # Quick decode (no decode dir)
```

**What to look for**: `<uses-permission>` over-privilege; `<application android:debuggable="true">>` = trivial jdb attach; `<application android:allowBackup="true">>` enables `adb backup` data extraction; `<network-security-config>` for cleartext traffic; `<provider>`/`<receiver>`/`<service>` exported components (IPC attack surface); custom `<permission>` for privilege escalation.

### DEX (Dalvik Executable) format

Register-based VM with 16-bit instruction units. Modern apps use **DEX 038/039** (Android 12-14); DEX 035 was the baseline since Android 7.0. Headers: `string_ids`, `type_ids` (`Lcom/example/MyClass;`), `proto_ids`, `method_ids`, `class_defs`.

Decompile with jadx 1.5.x:
```bash
jadx -d output/ app.apk                    # Full decompile (Java)
jadx --no-imports -d output/ app.apk       # No auto-imports (faster)
jadx --deobf --deobf-min 3 --deobf-max 20 -d output/ app.apk   # Deobfuscation
jadx --show-bad-code -d output/ app.apk    # Show code even on decompile failures
jadx-cli --version                         # Verify 1.5.x
```

### Smali assembly patterns

Smali is the **human-readable assembly** for Dalvik. Essential for obfuscated apps and direct DEX patching. jadx 1.5.x emits Java; switch to Smali when jadx fails or for surgical patches.

```smali
.method protected onCreate(Landroid/os/Bundle;)V
    .registers 4
    invoke-virtual {v1, v2}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    const-string v0, "encrypted_token"
    sget-object v0, Lcom/example/Config;->API_KEY:Ljava/lang/String;
    return-void
.end method
```

Common opcodes: `invoke-virtual/static/direct/super`; `const-string/jumbo`; `sget*`/`sput*` (static); `iget*`/`iput*` (instance); `new-instance` + `invoke-direct`; `if-eqz/nez/eq`; `return-void` / `return v0` / `return-object v0`.

Patch + sign workflow:
```bash
# Edit smali in decoded/, then:
apktool b decoded/ -o patched.apk
apksigner sign --ks debug.keystore --ks-key-alias androiddebugkey patched.apk
zipalign -p 4 patched.apk aligned.apk
```

### Native libraries

Extract from APK and analyze with Ghidra / IDA Pro / Binary Ninja / Capstone:
```bash
unzip -j app.apk "lib/arm64-v8a/*.so" -d native_libs/
readelf -h native_libs/libnative.so

# Capstone 6 disassembly (Python)
python3 -c "
import capstone
with open('native_libs/libnative.so','rb') as f: data=f.read()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
for i in md.disasm(data, 0x1000):
    if i.address > 0x1100: break
    print(f'0x{i.address:x}:\t{i.mnemonic}\t{i.op_str}')
"
```

**JNI RegisterNatives hook (resolves dynamically-registered native methods)**:
```javascript
const registerNatives = Module.findExportByName("libnative.so", "RegisterNatives");
Interceptor.attach(registerNatives, {
    onEnter(args) {
        const className = args[1].readCString();
        const methodCount = args[3].toUInt32();
        const methods = args[2];
        console.log(`RegisterNatives: ${className} (${methodCount} methods)`);
        for (let i = 0; i < methodCount; i++) {
            const offset = i * Process.pointerSize * 3;
            console.log(`  ${methods.add(offset).readPointer().readCString()}` +
                `${methods.add(offset + Process.pointerSize).readPointer().readCString()}` +
                ` -> ${methods.add(offset + Process.pointerSize*2).readPointer()}`);
        }
    }
});
```

### App Bundle (AAB)

Google Play distribution format since 2021 (per-device APK generation):
```
app.aab (ZIP)
├── BUNDLE-METADATA/    (dependencies.pb, native.pb)
├── base/
│   ├── manifest/AndroidManifest.xml   (binary AXML)
│   ├── dex/   (classes.dex, classes2.dex)
│   ├── lib/{arm64-v8a,armeabi-v7a}/
│   ├── res/, assets/
├── asset-pack-*/                       (optional, separate delivery)
└── META-INF/
```

Analysis:
```bash
# Direct AAB inspection
unzip -p app.aab base/manifest/AndroidManifest.xml > manifest.bin
aapt2 dump xmltree app.aab --file base/manifest/AndroidManifest.xml

# Generate universal APK via bundletool
bundletool build-apks --bundle=app.aab --output=app.apks --universal
unzip -p app.apks universal.apk > universal.apk

# Direct DEX + native extraction
unzip -j app.aab "base/dex/*.dex" -d dex/
unzip -j app.aab "base/lib/arm64-v8a/*.so" -d native/
```

### apktool 3.x workflow

apktool 3.x (full support in MobSF 4.5.2 since 10 ago 2026):
```bash
apktool d app.apk -o decoded/ -f              # Full decode
apktool d -s -f -o decoded/ app.apk           # Resources only (no sources)
apktool b decoded/ -o patched.apk             # Rebuild after edits

# Generate debug keystore (one-time)
keytool -genkey -v -keystore debug.keystore -storepass android \
    -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000
apksigner sign --ks debug.keystore --ks-pass pass:android --key-pass pass:android \
    --ks-key-alias androiddebugkey patched.apk
```

### jadx 1.5.x workflow

jadx 1.5.x added stronger Kotlin metadata, sealed class handling, and ARM64 metadata awareness.
```bash
jadx -d output/ app.apk                       # Basic decompile
jadx --export-gradle -d output/ app.apk       # Export as Gradle project
jadx-gui                                       # GUI mode (visual navigation)
```

Alternative CLI: `jadx-cli` (same binaries). Community migrated from dex2jar to jadx; use dex2jar only for niche compatibility.

## iOS RE

### IPA structure

```
app.ipa (ZIP container)
├── Payload/
│   └── AppName.app/
│       ├── AppName                          (Mach-O executable)
│       ├── Info.plist                       (binary plist, decode with plutil)
│       ├── PkgInfo                          (APKRInstaller + Content type)
│       ├── _CodeSignature/
│       │   └── CodeResources                (v2 signature)
│       ├── embedded.mobileprovision        (provisioning profile)
│       ├── Frameworks/                      (bundled dylibs)
│       │   ├── MyFramework.framework/
│       │   └── SwiftUI.framework/
│       ├── Assets.car                       (compiled assets)
│       ├── en.lproj/                        (localized resources)
│       └── PlugIns/                         (app extensions)
└── Symbols/                                  (only in TestFlight/dSYM builds)
```

Quick inspection:
```bash
unzip -l app.ipa
plutil -p Payload/AppName.app/Info.plist    # Convert binary plist → XML
codesign -dv Payload/AppName.app            # Verify signature
otool -L Payload/AppName.app/AppName        # Linked dylibs
nm -gU Payload/AppName.app/AppName          # Exported symbols
```

### Mach-O Universal binaries

iOS apps may ship as **fat binaries** (multiple architectures in one file):
```bash
# Check architectures
lipo -info Payload/AppName.app/AppName
# Architectures in the fat binary: arm64

# Extract specific arch
lipo -extract arm64 Payload/AppName.app/AppName -output app-arm64

# Inspect Mach-O header
otool -h app-arm64
otool -l app-arm64                           # Load commands
otool -s __TEXT __cstring app-arm64          # String section
```

Load commands to check:
- `LC_BUILD_VERSION` (replaced LC_VERSION_MIN_IPHONEOS in 11+) — minimum iOS version
- `LC_ENCRYPTION_INFO_64` — encrypted (App Store apps)
- `LC_MAIN` — entry point offset
- `LC_DYLD_EXPORTS_TRIE` / `LC_DYLD_CHAINED_FIXUPS` — modern pointer fixups
- `LC_LOAD_DYLIB` / `LC_LOAD_WEAK_DYLIB` — linked frameworks
- `LC_FUNCTION_STARTS` / `LC_DATA_IN_CODE` — function/data boundaries

### Code signatures + entitlements

iOS apps carry mandatory code signatures:
```bash
# Verify signature
codesign -dv --verbose=4 Payload/AppName.app

# Display entitlements (embedded.mobileprovision for App Store, codesign for sideloaded)
codesign -d --entitlements - Payload/AppName.app
# or
cat Payload/AppName.app/embedded.mobileprovision | openssl smime -in - -inform der -verify -noverify -outform xml
```

Key entitlements for security audit:
- `com.apple.developer.in-app-payments` — IAP entitlement
- `get-task-allow` — allows `task_for_pid` from other processes (debugging, attach)
- `com.apple.developer.networking.wifi-info` — WiFi BSSID access (location fingerprinting)
- `keychain-access-groups` — shared keychain with other apps (same team)
- `com.apple.developer.icloud-container-identifiers` — iCloud data access
- `com.apple.security.application-groups` — app group for IPC

### Dyld Shared Cache (IDA 9.4 reimagined)

iOS system frameworks are stored in the **dyld_shared_cache** (one file per iOS version, contains hundreds of system dylibs merged). Locating:
```bash
# On device (jailbroken)
ls /System/Library/Caches/dyld/

# Extracted from IPSW
# Cache path:  /System/Library/Caches/dyld/dyld_shared_cache_*
```

IDA 9.4 (jul 2026) added a **completely reimagined Dyld Shared Cache** workflow:
- Supports iOS 27 (forward-compatibility)
- Objective-C method prototypes recovered automatically
- `libobjcMsgSend` stubs auto-resolved to actual methods
- Faster cache loading via improved symbol table parsing

In Ghidra 12.1.4, use the **Dyld Cache Analyzer** plugin (built-in since 11.x).

### Swift calling convention (IDA 9.4 / Ghidra 12.1.4)

Swift uses a **distinctive calling convention** with self/async context in dedicated registers:
- **arm64**: `x20` = `self` reference; `x21` = async context; flags in `x22`
- **x86-64**: `r14` = `self` reference; `r15` = async context; flags in `r13`

IDA Pro 9.4 decompiler now recognizes:
- `__swiftself` — the `self` parameter
- `__swiftasync` — async function context
- `__swiftthrows` — throwing function marker
- `__swiftcall` — stripped binaries recover these automatically

In Ghidra 12.1.4, the **Microsoft Demangler** handles Swift mangling with new output options.

### Jailbroken iOS analysis

MobSF 4.5.1 (06 jul 2026) added **Jailbroken iOS Device support** (early beta). Compatible jailbreaks: **Checkra1n** (iOS 12–14, A7–A11), **Palera1n** (iOS 15–17, A8–A11), **Dopamine** (iOS 15–16.6.1, A12+).

Setup flow:
```bash
# Jailbreak device, then SSH (default password: alpine)
ssh root@<device-ip>

# Install + start Frida server matching your host version
curl -O https://github.com/frida/frida/releases/download/17.18.0/frida-server-17.18.0-ios-arm64.xz
unxz frida-server-17.18.0-ios-arm64.xz
scp frida-server-17.18.0-ios-arm64 root@<device-ip>:/usr/sbin/frida-server
ssh root@<device-ip> "chmod +x /usr/sbin/frida-server && /usr/sbin/frida-server &"

# Verify from host
frida-ps -U                                # List USB device processes

# Connect via MobSF 4.5.1+ for dynamic analysis
# Settings → Dynamic Analyzer → iOS Device
```

## Frida 17.x for mobile

### Android injection modes

**Three modes** for injecting Frida into Android processes:

1. **Gadget injection** (no root required, repackage APK):
   ```bash
   # 1. Download frida-gadget
   frida-gadget-17.18.0-android-arm64.so.xz
   unxz frida-gadget-17.18.0-android-arm64.so.xz

   # 2. Inject into APK
   apktool d app.apk -o decoded/
   cp frida-gadget-17.18.0-android-arm64.so decoded/lib/arm64-v8a/libfrida-gadget.so
   apktool b decoded/ -o patched.apk
   apksigner sign --ks debug.keystore --ks-key-alias androiddebugkey patched.apk

   # 3. Install patched APK
   adb install patched.apk

   # 4. Attach from host
   frida -H 127.0.0.1:8888 -f com.example.app --no-pause
   ```

2. **frida-server** (rooted device, recommended for pentest):
   ```bash
   # On device (after `adb push` + chmod +x)
   /data/local/tmp/frida-server-17.18.0-android-arm64 &

   # From host
   frida -U -f com.example.app                # Spawn + inject
   frida -U --codeshare <script>             # Community scripts
   ```

3. **Spawn-gating** (17.16+, fail-safe watchdog):
   ```bash
   frida -U -f com.example.app --no-pause -l bypass.js
   # `--no-pause` injects scripts BEFORE app initializes — bypasses most anti-Frida checks
   # The 17.16 watchdog disables itself if it hangs (avoids runaway gates).
   ```

### iOS injection (Barebone XNU kext in 17.18+)

Frida 17.18.0 (09 set 2026) added **Barebone XNU agent** that runs as a `.kext` loaded natively via `/dev/frida` (previously required GDB/QEMU/JTAG). For **Jailbroken iOS** (most common in 2026 pentest):
```bash
# Install frida-server on jailbroken device (see §Jailbroken iOS above)
frida -U -f com.example.app                # Spawn + inject
frida-ps -Uai | grep com.example          # Find PID by name
# Use with MobSF 4.5.3 Dynamic Analyzer (iOS Device mode)
```

For **Barebone** (advanced, kernel research): build/install barebone `.kext` on macOS host or jailbroken iOS — documented in Frida 17.18 release notes.

### Java.perform / ObjC.classes patterns

**Android (Java runtime)** — `Java.perform` runs on app's main thread (VM attached):
```javascript
Java.perform(function() {
    const MyClass = Java.use("com.example.app.MyClass");
    MyClass.encrypt.implementation = function(data, key) {
        const result = this.encrypt(data, key);  // original
        return result;
    };

    // Hook constructor (overloaded by signature)
    const URL = Java.use("java.net.URL");
    URL.$init.overload("java.lang.String").implementation = function(url) {
        return this.$init(url);
    };

    // Enumerate loaded classes (find target by prefix)
    Java.enumerateLoadedClasses({
        onMatch(c) { if (c.includes("com.example")) console.log(c); },
        onComplete() {}
    });
});
```

**iOS (Objective-C runtime)** — `ObjC.classes` enumerates all registered classes; Swift dispatches via ObjC bridge:
```javascript
// Hook NSURLSession.dataTaskWithRequest:completionHandler:
const orig = ObjC.classes.NSURLSession['- dataTaskWithRequest:completionHandler:'];
Interceptor.attach(orig.implementation, {
    onEnter(args) {
        const req = new ObjC.Object(args[2]);
        console.log(`[NSURLSession] ${req.HTTPMethod()} ${req.URL().absoluteString()}`);
    }
});

// Hook Swift UIViewController.viewDidLoad (works via ObjC dispatch)
const vc = ObjC.classes.UIViewController['- viewDidLoad'];
Interceptor.attach(vc.implementation, {
    onEnter(args) { console.log(`[viewDidLoad] ${new ObjC.Object(args[0]).$className}`); }
});
```

### Stalker v2 for code coverage

17.x Stalker improvements: **AVX-512 save/restore** (avoids corruption on AVX-512 code); **CodeSegment revival** for modern iOS (17.15+, critical for iOS 17.6+); **`Gum.Memory.patch_code` safe mode** (17.15+).

```javascript
Interceptor.attach(Module.findExportByName("libcrypto.so", "EVP_EncryptFinal_ex"), {
    onEnter(args) {
        this.tid = Process.getCurrentThreadId();
        Stalker.follow(this.tid, {
            events: { call: true, ret: false, exec: true },
            onCallSummary(summary) { console.log(JSON.stringify(summary, null, 2)); }
        });
    },
    onLeave(retval) { Stalker.unfollow(this.tid); Stalker.flush(); }
});
```

Real-world hooking examples (Android KeyStore, iOS Keychain, URLSession, JSON) are in §Hooking patterns below.

## MobSF 4.5.3 workflow

### Static analysis

```bash
docker pull opensecurity/mobile-security-framework-mobsf:4.5.3
docker run -itd --name mobsf -p 8000:8000 opensecurity/mobile-security-framework-mobsf:4.5.3

# Upload via REST API:
curl -X POST -F "file=@app.apk" http://localhost:8000/api/v1/upload       # returns scan hash
curl http://localhost:8000/api/v1/report_pdf?hash=<hash> -o report.pdf
curl http://localhost:8000/api/v1/view_source?hash=<hash>&type=xml        # v4.5.3: decompiled AndroidManifest XML
```

Static analysis extracts: manifest analysis (permissions, exported components, debug flags, allowBackup); code analysis (hardcoded secrets, crypto API misuse); API surface (all classes/methods/exports); native libs (ELF/Mach-O headers, suspicious API calls); resources (URLs, IPs, emails, base64 blobs); certs (chain, weak algos, expired).

### Dynamic analysis (Frida 17+)

MobSF 4.4.1 (31 ago 2025) added **Frida 17+ support** (breaking change: requires Frida server >= 17). Corellium iOS devices also require Frida >= 17.
```bash
# Setup on rooted Android (or jailbroken iOS for MobSF 4.5.1+)
adb push frida-server-17.18.0-android-arm64 /data/local/tmp/
adb shell chmod 755 /data/local/tmp/frida-server
adb shell /data/local/tmp/frida-server &

# MobSF web UI → Dynamic Analyzer → Configure scripts (ssl-pinning-bypass, root-detection-bypass, etc.)
# MobSF spawns app via Frida, captures HTTPS via mitmdump, logs hooked APIs, generates report
```

### REST API integration

```python
import requests

MOBSF_URL = "http://localhost:8000/api/v1"
HEADERS = {"Authorization": "<your-api-key>"}

def upload(file_path):
    with open(file_path, "rb") as f:
        return requests.post(f"{MOBSF_URL}/upload", files={"file": f}, headers=HEADERS).json()["hash"]

def get_report(scan_hash):
    return requests.post(f"{MOBSF_URL}/report", data={"hash": scan_hash}, headers=HEADERS).json()

def view_source(scan_hash, file_path, file_type="java"):
    """v4.5.3: type=xml supported for decompiled AndroidManifest"""
    r = requests.post(f"{MOBSF_URL}/view_source",
                      data={"hash": scan_hash, "file": file_path, "type": file_type}, headers=HEADERS)
    return r.content.decode()

# Usage
hash_id = upload("app.apk")
report = get_report(hash_id)
manifest_xml = view_source(hash_id, "AndroidManifest.xml", file_type="xml")
```

## Anti-RE bypass

### Anti-debug (Android ptrace, iOS sysctl)

**Android `ptrace` detection** — apps call `ptrace(PTRACE_TRACEME, ...)` on themselves; if already traced, returns -1:
```javascript
Interceptor.attach(Module.findExportByName(null, "ptrace"), {
    onEnter(args) { if (args[0].toInt32() === 0) args[0] = ptr("17"); },  // PTRACE_DETACH
    onLeave(retval) { retval.replace(ptr("0x0")); }
});
```

**iOS `sysctl` detection** — checks `P_TRACED` flag in `kinfo_proc`:
```javascript
Interceptor.attach(Module.findExportByName(null, "sysctl"), {
    onLeave(retval) {
        const infoPtr = this.context.x1;  // second arg (info ptr) on arm64
        const flagOffset = 0x100;  // platform-specific
        infoPtr.add(flagOffset).writeU8(infoPtr.add(flagOffset).readU8() & ~0x08);  // clear P_TRACED
    }
});
```

### Anti-Frida detection

Apps look for: `/tmp/frida-*` paths, port **27042** (default), `frida-agent`/`GumJS` strings in `/proc/self/maps`, `frida-agent.so` library.

**Bypass approaches**:
```bash
# 1. Spawn-gating — inject BEFORE anti-Frida checks run (most reliable)
frida -U -f com.example.app --no-pause -l bypass.js

# 2. Custom port (avoid 27042 detection)
frida-server -l 0.0.0.0:31337
frida -H 127.0.0.1:31337 -f com.example.app
```

```javascript
// 3. Hide Frida in process memory + filesystem
const mod = Process.findModuleByName("frida-agent");
if (mod) mod.name = "legit_system_lib";

Interceptor.attach(Module.findExportByName(null, "open"), {
    onEnter(args) {
        const path = args[0].readUtf8String();
        if (path && path.includes("/tmp/frida")) {
            args[0] = Memory.allocUtf8String("/tmp/.systemd-private");
        }
    }
});
```

### Anti-root / jailbreak detection

**Android checks**: `/system/xbin/su`, Magisk artifacts (`/sbin/magisk`, `/data/adb/magisk`), `Build.TAGS=test-keys`, `ro.debuggable=1`.

**iOS checks**: `/Applications/Cydia.app`, `/Library/MobileSubstrate`, `/bin/bash`, `/usr/sbin/sshd`, `/private/var/lib/apt/`.

**Frida bypass (Android)** — hook `File.exists` and `Runtime.exec`:
```javascript
Java.perform(function() {
    const File = Java.use("java.io.File");
    File.exists.implementation = function() {
        return /su|magisk|supersu/i.test(this.getAbsolutePath()) ? false : this.exists();
    };
    const Runtime = Java.use("java.lang.Runtime");
    Runtime.exec.overload("java.lang.String").implementation = function(cmd) {
        return /su|magisk/i.test(cmd) ? null : this.exec(cmd);
    };
});
```

**Frida bypass (iOS)** — hook `NSFileManager.fileExistsAtPath` and `fork`:
```javascript
const jailbreakPaths = ["/Applications/Cydia.app", "/Library/MobileSubstrate/MobileSubstrate.dylib",
                        "/bin/bash", "/usr/sbin/sshd", "/etc/apt"];
ObjC.classes.NSFileManager['- fileExistsAtPath:'].implementation = function(path) {
    const p = new ObjC.Object(path).toString();
    return !jailbreakPaths.some(jp => p.includes(jp)) && this.fileExistsAtPath_(path);
};
Interceptor.attach(Module.findExportByName(null, "fork"), {
    onLeave(retval) { retval.replace(ptr("0xffffffff")); }
});
```

### Anti-LLM (magic strings)

CAPA 9.4.0 (01 abr 2026) added `terminate-anthropic-session-via-magic-strings` rule. Apps detect LLM agents via:
- HTTP headers: `Reply-To`, `X-Claude-*`, `OpenAI-Organization`, `Anthropic-Version`
- API key prefixes in memory: `sk-`, `sk-ant-`
- JSON response patterns matching Claude/GPT format

Frida bypass: hook `HttpURLConnection.setRequestProperty` and strip suspicious headers.

### Play Integrity / Device Attestation

Google's replacement for deprecated SafetyNet Attestation:
- **MEETS_DEVICE_INTEGRITY** — genuine device (locked bootloader)
- **MEETS_BASIC_INTEGRITY** — passes CTS (may be rooted)
- **MEETS_STRONG_INTEGRITY** — hardware-backed key attestation

Bypass: **Magisk 27+ + Shamiko/Zygisk**; **Play Integrity Fix** (open-source, patches Play Services); custom ROM (GrapheneOS, CalyxOS). Frida cannot bypass hardware attestation (MEETS_STRONG_INTEGRITY); requires OS-level mods or patched Play Services.

## Mobile-specific RE frameworks

### Flutter (libapp.so, libflutter.so)

Flutter apps compile Dart to AOT native code. Files: `lib/arm64-v8a/{libapp.so, libflutter.so, lib<plugin>.so}`. Tools:
- **Blutter** (community fork `aauuudddddd/blutter`) — reconstruct class/function names from libapp.so
- **reFlutter** (`aauuudddddd/reFlutter`) — patch libapp.so for easier inspection
- **Doldisasm** — disassembly tool

```bash
python3 blutter.py libapp.so arm64                       # → classes.txt, methods.txt
python3 reflutter.py --bundle-id com.example.app --input app.apk --output patched.apk
```

### React Native (Hermes bytecode, JSC bundles)

**Two engines**: **Hermes** (default since RN 0.70+, pre-compiled bytecode) and **JSC** (legacy, text JS bundle). Both in `assets/index.android.bundle`.

Tools: **hbctool** (`bongtthan/hbctool`), **hermes-dec** (`bongtthan/hermes-dec`).

```bash
unzip -p app.apk assets/index.android.bundle > hermes.bc
hbctool disasm hermes.bc output_dir/
strings hermes.bc | grep -E 'https?://' | sort -u        # extract API endpoints
```

### Xamarin (DLL in APK)

Ship .NET DLLs in `assemblies/`. Runtime libs in `lib/.../{libmonodroid.so, libmonosgen-2.0.so}`.

RE tools: **ILSpy** (CLI/GUI), **dnSpy** (debugger+decompiler), **dotPeek** (commercial), **Mono.Cecil** (library).

```bash
unzip -j app.apk "assemblies/*.dll" -d assemblies/
ilspycmd MyApp.dll > MyApp.decompiled.cs
```

### Cordova/Ionic (WebView + assets)

HTML/JS wrapped in WebView; source often **unminified** in `assets/www/{index.html, js/app.js, plugins/}`. RE is essentially **web RE** (Chrome DevTools, js-beautify).

RE is essentially **web RE** (use Chrome DevTools, js-beautify, etc.).

## Hooking patterns (real examples)

### Hook Android KeyStore + Cipher (extract crypto keys)

```javascript
Java.perform(function() {
    const Cipher = Java.use("javax.crypto.Cipher");
    const KeyStore = Java.use("java.security.KeyStore");

    // Track key derivation + IV
    Cipher.init.overload("int", "java.security.Key").implementation = function(opmode, key) {
        const encoded = key.getEncoded && key.getEncoded();
        if (encoded) console.log(`[Cipher.init] algo=${key.getAlgorithm()} key=${hexdump(encoded)}`);
        return this.init(opmode, key);
    };

    // Capture plaintext + ciphertext at encryption boundary
    Cipher.doFinal.overload("[B").implementation = function(input) {
        const result = this.doFinal(input);
        console.log(`[Cipher.doFinal] in=${hexdump(input)} out=${hexdump(result)}`);
        return result;
    };

    // Extract raw keys by alias
    KeyStore.getKey.overload("java.lang.String", "[C").implementation = function(alias, password) {
        const key = this.getKey(alias, password);
        const encoded = key && key.getEncoded && key.getEncoded();
        if (encoded) console.log(`[KeyStore.getKey] alias=${alias} key=${hexdump(encoded)}`);
        return key;
    });
});
```

### Hook iOS Keychain (intercept tokens/secrets)

```javascript
const SecItemCopyMatching = Module.findExportByName("Security", "SecItemCopyMatching");
Interceptor.attach(SecItemCopyMatching, {
    onEnter(args) {
        const query = args[0];
        // query is CFDictionary with kSecClass/kSecAttrService/kSecAttrAccount
        const dict = new ObjC.classes.NSDictionary(query);
        const kSecClass = ObjC.classes.NSString.stringWithString_("kSecClass");
        if (dict) {
            const cls = dict.objectForKey_(kSecClass);
            if (cls) console.log(`[SecItemCopyMatching] kSecClass=${cls.toString()}`);
        }
    },
    onLeave(retval) { console.log(`[SecItemCopyMatching] status=${retval.toInt32()}`); }
});

// Also hook SecItemAdd for write interception
const SecItemAdd = Module.findExportByName("Security", "SecItemAdd");
Interceptor.attach(SecItemAdd, {
    onEnter(args) { console.log(`[SecItemAdd] query=${args[0].readCString() || "(binary dict)"}`); }
});
```

### Hook URLSession (network interception)

```javascript
// dataTask (most common) — log URL + headers
const dataTask = ObjC.classes.NSURLSession['- dataTaskWithRequest:completionHandler:'];
Interceptor.attach(dataTask.implementation, {
    onEnter(args) {
        const req = new ObjC.Object(args[2]);
        console.log(`[URLSession] ${req.HTTPMethod()} ${req.URL().absoluteString()}`);
        const headers = req.allHTTPHeaderFields();
        if (headers) console.log(`[URLSession] headers=${headers.toString()}`);
    }
});

// Catch ALL request types via NSURLSessionTask.resume
ObjC.classes.NSURLSessionTask['- resume'].implementation = function() {
    const req = this.currentRequest();
    if (req) console.log(`[URLSessionTask resume] ${req.URL().absoluteString()}`);
    return this.resume();
};
```

### Hook JSON serialization (token extraction)

```javascript
// Android: track JSON keys containing "token" / "auth" / "secret"
Java.perform(function() {
    const JSONObject = Java.use("org.json.JSONObject");
    JSONObject.$init.overload("java.lang.String").implementation = function(json) {
        if (/token|auth/i.test(json)) console.log(`[JSONObject ctor] ${json}`);
        return this.$init(json);
    };
    JSONObject.put.overload("java.lang.String", "java.lang.Object").implementation = function(key, value) {
        if (/token|secret/i.test(key.toString())) console.log(`[JSONObject.put] ${key}=${value}`);
        return this.put(key, value);
    };
});

// iOS
const NSJSONSerialization = ObjC.classes.NSJSONSerialization;
Interceptor.attach(NSJSONSerialization['+ dataWithJSONObject:options:error:'].implementation, {
    onEnter(args) {
        const obj = new ObjC.Object(args[2]);
        if (/token|auth/i.test(obj.toString())) console.log(`[NSJSONSerialization] ${obj.toString()}`);
    }
});
```

## Common pitfalls

- **Android 14+ scoped storage**: app data in `/data/data/<pkg>/` requires root or `adb backup` (deprecated)
- **iOS 17.6+ CodeSegment revival**: Frida < 17.15 cannot reliably hook some system frameworks; **upgrade to 17.18+**
- **APK v3.1/v4 signing**: old apksigner (v1/v2 only) fails to verify; ensure apksigner 37.0.0+
- **Hermes bytecode encryption**: many production React Native apps encrypt `index.android.bundle` with custom keys (no plaintext strings)
- **Flutter AOT snapshots**: same as Hermes — strings obfuscated, requires specialized tools (Blutter/reFlutter)
- **String encryption in DEX**: Smali shows `const-string` with Base64 or XOR'd strings; deobfuscate before analysis
- **Anti-tampering (Play Integrity)**: cannot bypass MEETS_STRONG_INTEGRITY via Frida alone — needs Magisk+Shamiko or hardware fix
- **iOS encrypted app binaries**: App Store binaries encrypted with device-specific key; require runtime decryption or jailbroken device with decrypted cache
- **Magisk detection**: MagiskHide/Zygisk now detectable via `/proc/mounts` listing + `BuildProp` parsing; use modern Magisk 27+ with DenyList
- **dex2jar + jadx mismatch**: dex2jar output is inferior to direct jadx decompilation; prefer jadx directly
- **Objection deprecation**: Objection 1.11 [VERIFY] — repo status uncertain (last known release); use raw Frida for stability

## Cross-references

- **`reverse-engineer`** — Frida 17.18 features (Stalker v2, Barebone, LanguageServer), IDA Pro 9.4, Ghidra 12.1.4, Binary Ninja 6.0 Krypton, capstone 6 ARM64 disassembly
- **`malware-analyst`** — Mobile malware analysis workflow (MalwareBazaar samples, sandbox submission), FLOSS 3.1.1 + QUANTUMSTRAND β3 for obfuscated strings
- **`binary-analysis-patterns`** — ARM64 Thumb2 disassembly patterns, register/flag calling conventions
- **`firmware-analyst`** — IoT/embedded RE if mobile app interfaces with custom hardware
- **`protocol-reverse-engineering`** — mitmproxy 12.2.3 for HTTPS interception (bypass SSL pinning), Wireshark 4.6.8 for low-level capture
- **`ai-assisted-re`** — MCP servers for Binary Ninja (only commercial disassembler with first-party MCP) drive Android RE workflows
- **`anti-reversing-techniques`** — Comprehensive anti-RE bypass catalog (stub — verify status)

## Integração com system-dissector

Esta skill é um **instrumento** consumido por `system-dissector` durante as fases 2-4:

- **Quando invocar**: Phase 2 (deep-dive) ou Phase 4 (extract) do `system-dissector`
- **Tipo de alvo**: source | binary | mobile | firmware | protocol
- **Output esperado**: wiki page ou extract component
- **Templates relacionados**: `templates/deep-dive-{architecture,module}.md.template`, `templates/extract-{components,patterns}.md.template`

**Contrato**:
- Path canônico: `dissects/<sistema>/<fase>/<arquivo>.md`
- Use `evidence: verified|estimated` em todo `file:line`
- Rubrica C1-C6 quando aplicável (consulte `extract-components.md.template`)
- Companion: `neodoo-integrate` para port-plan (Phase 5)

## References

- Frida 17.18.0 release notes (frida.re, 09 set 2026); 17.15.x CodeSegment revival (jun 2026)
- MobSF v4.5.3 (21 set 2026); v4.5.2 (10 ago 2026 — apksigner 37.0.0, apktool 3.x); v4.5.1 (06 jul 2026 — Jailbroken iOS beta); v4.4.1 (31 ago 2025 — Frida 17+ support, Corellium requires Frida >=17)
- apktool 3.x (iBotPeaches/apktool); jadx 1.5.x (skylot/jadx); Objection [VERIFY] (sensepost/objection, last known 1.11); LIEF 0.17 (MobSF 4.5.3 integration)
- CAPA 9.4.0 (01 abr 2026) — anti-LLM rule `terminate-anthropic-session-via-magic-strings`
- Android Studio / apksigner 37.0.0 (Android SDK build-tools)
- Hermes bytecode — `bongtthan/hbctool`, `bongtthan/hermes-dec`; Flutter — `aauuudddddd/blutter`, `aauuudddddd/reFlutter`
- Capstone 6.0.0-Alpha11 (21 set 2026) / 5.0.9 stable — ARM64 Thumb2 disassembly
- Apple Dyld Shared Cache + Swift calling convention (IDA Pro 9.4 decompiler, jul 2026)