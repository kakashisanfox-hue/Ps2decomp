import unittest
from tools.mips_function_map import parse_text, scan
from test_mips_callgraph import make_elf


class FunctionMapTests(unittest.TestCase):
    def test_entry_and_direct_call_seeds(self):
        # jal 0x100010; nop; jr ra; nop; jr ra; nop
        elf=make_elf([0x0c040004,0,0x03e00008,0,0x03e00008,0])
        result=scan(elf)
        self.assertEqual(result['function_seed_count'],2)
        self.assertEqual(result['direct_call_sites'],1)
        self.assertEqual(result['functions'][0]['start'],'0x100000')
        self.assertEqual(result['functions'][1]['start'],'0x100010')
        self.assertEqual(result['truncated_function_count'],0)
        self.assertGreater(result['unique_instructions_covered_estimate'],0)

    def test_loop_terminates(self):
        elf=make_elf([0x1000ffff,0,0x03e00008,0])
        result=scan(elf)
        self.assertEqual(result['function_seed_count'],1)
        self.assertEqual(result['truncated_function_count'],0)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            parse_text(b'bad')

    def test_max_function_limit(self):
        elf=make_elf([0x0c040004,0,0x03e00008,0,0x03e00008,0])
        with self.assertRaises(ValueError):
            scan(elf,max_functions=1)


if __name__=='__main__':
    unittest.main()
