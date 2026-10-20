#include <jni.h>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include <cstdio>
#include <algorithm>

namespace {
uint16_t u16(const uint8_t* p) { return uint16_t(p[0]) | uint16_t(p[1]) << 8; }
uint32_t u32(const uint8_t* p) { return uint32_t(u16(p)) | uint32_t(u16(p+2)) << 16; }
struct Segment { uint32_t addr, memSize; std::vector<uint8_t> data; };
std::string probe(const uint8_t* elf, size_t size) {
    if(size < 52 || std::memcmp(elf,"\177ELF",4) || elf[4]!=1 || elf[5]!=1 ||
       u16(elf+18)!=8) return "Invalid ELF32 little-endian MIPS executable";
    const uint32_t entry=u32(elf+24), phoff=u32(elf+28);
    const uint16_t phentsize=u16(elf+42), phnum=u16(elf+44);
    if(phentsize<32 || phnum>128 || uint64_t(phoff)+uint64_t(phentsize)*phnum>size)
        return "Invalid ELF program headers";
    std::vector<Segment> segments;
    for(unsigned i=0;i<phnum;i++) {
        const uint8_t* ph=elf+phoff+size_t(i)*phentsize;
        if(u32(ph)!=1) continue;
        uint32_t offset=u32(ph+4), vaddr=u32(ph+8), filesz=u32(ph+16), memsz=u32(ph+20);
        if(memsz<filesz || memsz>64*1024*1024 || uint64_t(offset)+filesz>size ||
           uint64_t(vaddr)+memsz>0x100000000ULL) return "Invalid PT_LOAD segment";
        Segment s; s.addr=vaddr;s.memSize=memsz;s.data.resize(memsz,0);
        std::memcpy(s.data.data(),elf+offset,filesz);
        segments.push_back(std::move(s));
    }
    char out[512];
    if(segments.empty()) return "ELF has no loadable PT_LOAD segments";
    for(const auto& seg:segments) {
        if(entry>=seg.addr && uint64_t(entry)+4<=uint64_t(seg.addr)+seg.memSize) {
            const uint32_t first=u32(seg.data.data()+entry-seg.addr);
            const uint32_t opcode=first>>26;
            std::snprintf(out,sizeof(out),
                "Native ARM64 ELF loader: OK\nPT_LOAD segments: %zu\n"
                "PS2 entry PC: 0x%08X\nFirst instruction: 0x%08X\n"
                "Instruction family: %s\n"
                "STATUS: original game code NOT executed. "
                "Static MMI translation and PS2 runtime are required.",
                segments.size(),entry,first,opcode==0x1c?"MMI (Emotion Engine)": "MIPS/R5900");
            return out;
        }
    }
    std::snprintf(out,sizeof(out),"Loaded %zu PT_LOAD segments, but entry 0x%08X is not mapped",
                  segments.size(),entry);
    return out;
}
}
extern "C" JNIEXPORT jstring JNICALL
Java_dev_downhill_nativeport_MainActivity_nativeProbe(JNIEnv* env,jclass,jbyteArray array) {
    if(!array) return env->NewStringUTF("No ELF bytes");
    jsize length=env->GetArrayLength(array);
    if(length<=0 || length>32*1024*1024)return env->NewStringUTF("ELF size outside supported range");
    jbyte* bytes=env->GetByteArrayElements(array,nullptr);
    if(!bytes)return env->NewStringUTF("Unable to access ELF bytes");
    std::string result=probe(reinterpret_cast<const uint8_t*>(bytes),size_t(length));
    env->ReleaseByteArrayElements(array,bytes,JNI_ABORT);
    return env->NewStringUTF(result.c_str());
}
extern "C" std::int32_t synthetic_mips_entry();
extern "C" JNIEXPORT jstring JNICALL
Java_dev_downhill_nativeport_MainActivity_status(JNIEnv* env,jclass) {
    return env->NewStringUTF(synthetic_mips_entry()==42?"ARM64 JNI loaded":"JNI self-check failed");
}
