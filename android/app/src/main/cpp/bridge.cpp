#include <jni.h>
extern "C" JNIEXPORT jstring JNICALL
Java_dev_downhill_nativeport_MainActivity_status(JNIEnv* env, jclass) {
    return env->NewStringUTF("ARM64 JNI bridge loaded. Game recompilation not integrated.");
}
