import struct
import unittest
from tools.mips_callgraph import inspect


def make_elf(words):
    code=b''.join(struct.pack('<I',w) for w in words)
    names=b'\x00.shstrtab\x00.text\x00'
    nameoff=0x80
    codeoff=0xa0
    shoff=(codeoff+len(code)+15)&~15
    blob=bytearray(shoff+3*40)
    blob[:16]=b'\x7fELF\x01\x01\x01'+bytes(9)
    struct.pack_into('<HHIIIIIHHHHHH',blob,16,2,8,1,0x100000,0,shoff,0,52,0,0,40,3,1)
    blob[nameoff:nameoff+len(names)]=names
    blob[codeoff:codeoff+len(code)]=code
    struct.pack_into('<IIIIIIIIII',blob,shoff+40,1,3,0,0,nameoff,len(names),0,0,1,0)
    struct.pack_into('<IIIIIIIIII',blob,shoff+80,11,1,6,0x100000,codeoff,len(code),0,0,4,0)
    return bytes(blob)


class CallGraphTests(unittest.TestCase):
    def test_call_and_return(self):
        # jal 0x100008; nop; jr ra; nop
        result=inspect(make_elf([0x0c040002,0,0x03e00008,0]))
        self.assertEqual(result['direct_call_sites'],1)
        self.assertEqual(result['top_call_targets'][0]['address'],'0x100008')
        self.assertEqual(result['return_instruction_candidates'],1)
        self.assertEqual(result['function_entry_candidates'], ['0x100000','0x100008'])
        self.assertEqual(result['direct_call_edges'][0]['source'], '0x100000')
        self.assertEqual(result['direct_call_edges'][0]['inside_text'], True)
        self.assertEqual(result['external_direct_call_count'], 0)
        self.assertEqual(len(result['input_sha256']), 64)

    def test_indirect_call_and_branch(self):
        result=inspect(make_elf([0x0320f809,0x1000ffff,0,0]))
        self.assertEqual(result['indirect_call_sites'],1)
        self.assertEqual(result['conditional_branch_count'],1)

    def test_outside_text_call(self):
        result=inspect(make_elf([0x0c080000,0,0x03e00008,0]))
        self.assertEqual(result['direct_call_sites'],0)
        self.assertEqual(result['external_direct_call_count'],1)
        self.assertEqual(result['external_direct_calls'][0]['target'],'0x200000')

    def test_limit_report(self):
        result=inspect(make_elf([0x0c040002,0,0x03e00008,0]),limit=0)
        self.assertEqual(result['direct_call_edges'],[])
        self.assertEqual(result['function_entry_candidates'],['0x100000','0x100008'])

    def test_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            inspect(b'not an elf')

if __name__=='__main__':
    unittest.main()
