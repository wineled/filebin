from elftools.elf.elffile import ELFFile
path = r"f:\CodingProjects\filebin\test-elf\test_dwarf.elf"
with open(path, 'rb') as f:
    elf = ELFFile(f)
    dwarf = elf.get_dwarf_info()
    for cu in dwarf.iter_CUs():
        lprog = dwarf.line_program_for_CU(cu)
        header = lprog.header
        file_entries = header.get('file_entry', [])
        for entry in lprog.get_entries():
            st = entry.state
            if not st:
                continue
            fi = st.file - 1
            if 0 <= fi < len(file_entries):
                fe = file_entries[fi]
                name = None
                if isinstance(fe, dict):
                    name = fe.get('name')
                else:
                    name = getattr(fe, 'name', None)
                try:
                    name_s = name.decode() if isinstance(name, (bytes, bytearray)) else str(name)
                except Exception:
                    name_s = repr(name)
                if 'test_dwarf.c' in name_s:
                    print(f'file={name_s}, line={st.line}, addr=0x{st.address:x}')
