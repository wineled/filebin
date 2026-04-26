#!/usr/bin/env python3
"""诊断 DWARF 行号表内容"""
import sys
from elftools.elf.elffile import ELFFile

elf = ELFFile(open(r"F:\CodingProjects\filebin\test-elf\test_dwarf.elf", 'rb'))
dwarfinfo = elf.get_dwarf_info()

print("=== 行号表内容 ===")
all_lines = set()
for cu in dwarfinfo.iter_CUs():
    lprog = dwarfinfo.line_program_for_CU(cu)
    header = lprog.header
    inc_dirs = header.get('include_directory', [])
    file_entries = header.get('file_entry', [])

    print(f"CU: {cu.cu_offset}")
    print("  include dirs:", [d.decode() for d in inc_dirs])
    print("  file entries:", [
        f"{fe.get('name', b'').decode()} (dir_idx={fe.get('directory_index', 0)})"
        for fe in file_entries
    ])
    for entry in lprog.get_entries():
        if entry.state:
            fe = file_entries[entry.state.file - 1] if entry.state.file <= len(file_entries) else None
            raw = fe.get('name', b'').decode() if fe else '?'
            dir_idx = fe.get('directory_index', 0) if fe else 0
            if dir_idx > 0 and dir_idx <= len(inc_dirs):
                full = inc_dirs[dir_idx - 1].decode() + '/' + raw
            else:
                full = raw
            print(f"  [{entry.state.file}] {full}  line={entry.state.line}  addr=0x{entry.state.address:x}")
            all_lines.add(entry.state.line)

print("\n=== 所有行号 (去重) ===")
print(sorted(all_lines))

print("\n=== 行号7相关条目 ===")
for cu in dwarfinfo.iter_CUs():
    lprog = dwarfinfo.line_program_for_CU(cu)
    header = lprog.header
    file_entries = header.get('file_entry', [])
    inc_dirs = header.get('include_directory', [])
    for entry in lprog.get_entries():
        if entry.state and entry.state.line == 7:
            fe = file_entries[entry.state.file - 1] if entry.state.file <= len(file_entries) else None
            raw = fe.get('name', b'').decode() if fe else '?'
            dir_idx = fe.get('directory_index', 0) if fe else 0
            if dir_idx > 0 and dir_idx <= len(inc_dirs):
                full = inc_dirs[dir_idx - 1].decode() + '/' + raw
            else:
                full = raw
            print(f"  {full}  line=7  addr=0x{entry.state.address:x}")
