#include <jni.h>
#include <cstdint>
extern "C" std::int32_t synthetic_mips_entry();
extern "C" JNIEXPORT jstring JNICALL
Java_dev_downhill_nativeport_MainActivity_status(JNIEnv* env, jclass) {
    if (synthetic_mips_entry() != 42) {
        return env->NewStringUTF("Synthetic MIPS ARM64 test FAILED");
    }
    return env->NewStringUTF("ARM64 native test passed: synthetic MIPS returns 42. Downhill not integrated.");
}
