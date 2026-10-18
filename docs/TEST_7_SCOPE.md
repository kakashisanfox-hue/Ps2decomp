# Test 7: Synthetic MIPS logic in Android ARM64

The app's JNI bridge now calls a tiny C++ equivalent of the earlier synthetic MIPS program and checks that the returned value is 42. This validates native linking and invocation on Android, but **does not** integrate actual PS2Recomp-generated output, recompile Downhill, or prove runtime execution on a phone.

The CI build checks APK packaging only. A device or emulator test would be required to confirm execution.

The real next gate is to generate C++ with PS2Recomp from a private copy of SLES_522.02 and integrate the output. Never commit proprietary executable or ISO to the public repository.
