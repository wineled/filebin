#!/usr/bin/env python3
"""检查 call 指令的操作数"""
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

with open('testfile.elf', 'rb') as f:
    elf = ELFFile(f)
    text = elf.get_section_by_name('.text')
    if text:
        code = text.data()
        base = text['sh_addr']
        
        md = Cs(CS_ARCH_X86, CS_MODE_64)
        md.detail = True
        
        # 查找 main 函数中的 call
        print('=== main 函数中的 call 指令详情 ===')
        for insn in md.disasm(code, base):
            if 0x140001454 <= insn.address < 0x140001490:
                if insn.mnemonic == 'call':
                    print(f'地址: 0x{insn.address:x}')
                    print(f'  操作数字符串: {insn.op_str}')
                    print(f'  操作数:')
                    for i, op in enumerate(insn.operands):
                        print(f'    [{i}] type={op.type}')
                        if hasattr(op, 'imm'):
                            print(f'        imm=0x{op.imm:x}')
                        if hasattr(op, 'reg'):
                            print(f'        reg={op.reg}')
                        if hasattr(op, 'size'):
                            print(f'        size={op.size}')
                    print()