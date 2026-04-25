from elftools.elf.elffile import ELFFile

with open('testfile.elf', 'rb') as f:
    elf = ELFFile(f)
    dwarfinfo = elf.get_dwarf_info()
    
    for cu in dwarfinfo.iter_CUs():
        lprog = dwarfinfo.line_program_for_CU(cu)
        header = lprog.header
        files = header.get('file_entry', [])
        
        print(f'Number of file entries: {len(files)}')
        # 文件条目是列表，索引从 0 开始
        for i, fe in enumerate(files):
            print(f'  [{i}] name={fe.get("name")}, dir={fe.get("dir_index")}')
        
        # 尝试用列表索引
        print('\nUsing list index:')
        for i, fe in enumerate(files):
            name = fe.get('name', b'')
            print(f'  [{i}] {name}')
            if b'test_dwarf.c' in name:
                print(f'  >>> Found test_dwarf.c at index {i}')