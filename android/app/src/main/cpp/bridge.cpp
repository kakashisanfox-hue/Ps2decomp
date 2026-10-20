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

struct EE {
    uint64_t gpr[32]{}; uint32_t pc=0;
    uint64_t steps=0; std::string stop;
    const std::vector<Segment>& segments;
    explicit EE(const std::vector<Segment>& seg):segments(seg){}
    bool read32(uint32_t addr,uint32_t& value)const{
        if(addr&3)return false;
        for(const auto& s:segments)if(addr>=s.addr && uint64_t(addr)+4<=uint64_t(s.addr)+s.memSize){
            value=u32(s.data.data()+addr-s.addr);return true;
        }
        return false;
    }
    bool step(){
        uint32_t word;
        if(!read32(pc,word)){stop="PC outside loaded memory";return false;}
        unsigned op=word>>26,rs=(word>>21)&31,rt=(word>>16)&31,rd=(word>>11)&31;
        unsigned sh=(word>>6)&31,fn=word&63;
        int64_t imm=int16_t(word&65535);
        uint32_t next=pc+4;
        bool branch=false,taken=false;uint32_t target=0;
        switch(op){
            case 0:
                switch(fn){
                    case 0: if(rd)gpr[rd]=uint64_t(int64_t(int32_t(uint32_t(gpr[rt])<<sh)));break;
                    case 2: if(rd)gpr[rd]=uint64_t(int64_t(int32_t(uint32_t(gpr[rt])>>sh)));break;
                    case 3: if(rd)gpr[rd]=uint64_t(int64_t(int32_t(int32_t(gpr[rt])>>sh)));break;
                    case 8: branch=true;taken=true;target=uint32_t(gpr[rs]);break;
                    case 9: branch=true;taken=true;target=uint32_t(gpr[rs]);if(rd)gpr[rd]=pc+8;break;
                    case 33: if(rd)gpr[rd]=uint64_t(int64_t(int32_t(uint32_t(gpr[rs])+uint32_t(gpr[rt]))));break;
                    case 35: if(rd)gpr[rd]=uint64_t(int64_t(int32_t(uint32_t(gpr[rs])-uint32_t(gpr[rt]))));break;
                    case 36: if(rd)gpr[rd]=gpr[rs]&gpr[rt];break;
                    case 37: if(rd)gpr[rd]=gpr[rs]|gpr[rt];break;
                    case 38: if(rd)gpr[rd]=gpr[rs]^gpr[rt];break;
                    case 42: if(rd)gpr[rd]=int64_t(gpr[rs])<int64_t(gpr[rt]);break;
                    default:goto unsupported;
                }break;
            case 2: branch=true;taken=true;target=((pc+4)&0xf0000000)|((word&0x3ffffff)<<2);break;
            case 3: branch=true;taken=true;target=((pc+4)&0xf0000000)|((word&0x3ffffff)<<2);gpr[31]=pc+8;break;
            case 4: case 5:
                branch=true;taken=(op==4?gpr[rs]==gpr[rt]:gpr[rs]!=gpr[rt]);
                target=uint32_t(pc+4+imm*4);break;
            case 6: case 7:
                branch=true;taken=(op==6?int64_t(gpr[rs])<=0:int64_t(gpr[rs])>0);
                target=uint32_t(pc+4+imm*4);break;
            case 9: if(rt)gpr[rt]=uint64_t(int64_t(int32_t(uint32_t(gpr[rs])+uint32_t(imm))));break;
            case 10: if(rt)gpr[rt]=int64_t(gpr[rs])<imm;break;
            case 11: if(rt)gpr[rt]=gpr[rs]<uint64_t(imm);break;
            case 12: if(rt)gpr[rt]=gpr[rs]&uint64_t(word&65535);break;
            case 13: if(rt)gpr[rt]=gpr[rs]|uint64_t(word&65535);break;
            case 14: if(rt)gpr[rt]=gpr[rs]^uint64_t(word&65535);break;
            case 15: if(rt)gpr[rt]=uint64_t(int64_t(int32_t(uint32_t(word&65535)<<16)));break;
            case 35: {
                uint32_t val=0,addr=uint32_t(gpr[rs]+imm);
                if(!read32(addr,val)){stop="LW from unmapped or unaligned address";return false;}
                if(rt)gpr[rt]=uint64_t(int64_t(int32_t(val)));
                break;
            }
            case 28: // PS2 MMI instructions need exact R5900 128-bit semantics.
                goto unsupported;
            default:goto unsupported;
        }
        gpr[0]=0;
        if(branch){
            // A branch delay slot must be interpreted; do not silently skip it.
            uint32_t delay=0;
            if(!read32(pc+4,delay)){stop="Unmapped branch delay slot";return false;}
            if(delay!=0){stop="Non-NOP branch delay slot requires full R5900 executor";return false;}
            pc=taken?target:pc+8;
        }else pc=next;
        ++steps;
        return true;
    unsupported:
        char buffer[128];
        std::snprintf(buffer,sizeof(buffer),"Unsupported R5900 instruction at 0x%08X: 0x%08X (op=%u)",pc,word,op);
        stop=buffer;return false;
    }
    std::string run(uint32_t entry){
        pc=entry;
        constexpr uint64_t budget=20000;
        while(steps<budget && step()){}
        if(stop.empty())stop="Instruction budget reached";
        char buffer[300];
        std::snprintf(buffer,sizeof(buffer),
            "REAL PS2 instruction executor (experimental)\\n"
            "Executed instructions: %llu\\nLast PC: 0x%08X\\nStop: %s\\n"
            "No graphics, audio, PS2 syscalls or gameplay implemented.",
            static_cast<unsigned long long>(steps),pc,stop.c_str());
        return buffer;
    }
};

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
            EE cpu(segments);
            std::string execution=cpu.run(entry);
            std::snprintf(out,sizeof(out),
                "Native ARM64 ELF loader: OK\nPT_LOAD segments: %zu\n"
                "PS2 entry PC: 0x%08X\nFirst instruction: 0x%08X\n"
                "Instruction family: %s\n"
                "%s",
                segments.size(),entry,first,opcode==0x1c?"MMI (Emotion Engine)": "MIPS/R5900",execution.c_str());
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
