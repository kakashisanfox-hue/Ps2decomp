plugins { id("com.android.application") }
android {
    namespace = "dev.downhill.nativeport"
    compileSdk = 35
    defaultConfig {
        applicationId = "dev.downhill.nativeport"
        minSdk = 26
        targetSdk = 28
        versionCode = 1
        versionName = "0.0.1-research"
        ndk { abiFilters += "arm64-v8a" }
    }
    externalNativeBuild { cmake { path = file("src/main/cpp/CMakeLists.txt") } }
}
