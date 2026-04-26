from elftools.elf.elffile import ELFFile
from collections import defaultdict

path = r"f:\CodingProjects\filebin\test-elf\test_dwarf.elf"
with open(path, 'rb') as f:
    elf = ELFFile(f)
    dwarf = elf.get_dwarf_info()
    files = set()
    matches = []
    for cu in dwarf.iter_CUs():
        lprog = dwarf.line_program_for_CU(cu)
        header = lprog.header
        file_entries = header.get('file_entry', [])
        inc_dirs = header.get('include_directory', [])
        print('CU:')
        print(' include dirs:')
        for i, d in enumerate(inc_dirs, 1):
            try:
                print(f'  {i}:', d.decode() if isinstance(d, (bytes, bytearray)) else d)
            except Exception:
                print('  ', d)
        print(' file entries:')
        for i, fe in enumerate(file_entries, 1):
            name = None
            dir_idx = None
            if isinstance(fe, dict):
                name = fe.get('name')
                dir_idx = fe.get('directory_index', 0)
            else:
                name = getattr(fe, 'name', None)
                dir_idx = getattr(fe, 'directory_index', 0)
            try:
                name_str = name.decode() if isinstance(name, (bytes, bytearray)) else str(name)
            except Exception:
                name_str = repr(name)
            print(f'  {i}: name={name_str}, dir_idx={dir_idx}')
            files.add(name_str)

        print('\nEntries with line 9 or small sample:')
        for entry in lprog.get_entries():
            st = entry.state
            if st is None:
                continue
            if st.line == 9:
                filestr = None
                file_idx = st.file - 1
                if 0 <= file_idx < len(file_entries):
                    fe = file_entries[file_idx]
                    if isinstance(fe, dict):
                        raw = fe.get('name')
                        dir_idx = fe.get('directory_index', 0)
                    else:
                        raw = getattr(fe, 'name', None)
                        dir_idx = getattr(fe, 'directory_index', 0)
                    try:
                        filestr = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
                    except Exception:
                        filestr = repr(raw)
                print(f' line 9 -> addr=0x{st.address:x}, file_idx={st.file}, file={filestr}')

    print('\nAll file names seen:')
    for fn in sorted(files):
        print(' -', fn)
