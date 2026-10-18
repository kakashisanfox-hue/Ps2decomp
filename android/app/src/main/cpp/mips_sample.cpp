#include <cstdint>
// Synthetic MIPS test: addiu $v0,$zero,42; jr $ra; nop.
// Equivalent host translation, NOT Downhill game code.
extern "C" std::int32_t synthetic_mips_entry() {
    return static_cast<std::int32_t>(42);
}
