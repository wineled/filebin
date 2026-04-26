#!/usr/bin/env python3
"""诊断 DWARF 行号表内容 for test_dwarf.c"""
import sys
from elftools.elf.elffile import ELFFile

elf = ELFFile(open(r"F:\CodingProjects\filebin\test-elf\test_dwarf.elf", 'rb'))
dwarfinfo = elf.get_dwarf_info()

for cu in dwarfinfo.iter_CUs():
    lprog = dwarfinfo.line_program_for_CU(cu)
    header = lprog.header
    file_entries = header.get('file_entry', [])
    inc_dirs = header.get('include_directory', [])

    for entry in lprog.get_entries():
        if entry.state and entry.state.file <= len(file_entries):
            fe = file_entries[entry.state.file - 1]
            raw = fe.get('name', b'').decode()
            if 'test_dwarf' in raw:
                dir_idx = fe.get('directory_index', 0)
                if dir_idx > 0 and dir_idx <= len(inc_dirs):
                    full = inc_dirs[dir_idx - 1].decode() + '/' + raw
                else:
                    full = raw
                print(f"  {full}  line={entry.state.line}  addr=0x{entry.state.address:x}")
