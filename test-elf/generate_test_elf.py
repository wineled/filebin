#!/usr/bin/env python3
"""
生成测试用的 ELF 文件（包含 DWARF 调试信息）
用于测试 log_call_finder.py
"""
import struct
import os

def create_simple_elf(output_path):
    """创建一个简单的 ELF 文件（64-bit, little endian）"""
    
    # ELF 魔数
    ELF_MAGIC = b'\x7fELF'
    
    # e_ident[16] = 16 bytes
    e_ident = [
        0x7f, 0x45, 0x4c, 0x46,  # EI_MAG: \x7fELF
        2,                        # EI_CLASS: 64-bit
        1,                        # EI_DATA: little endian
        1,                        # EI_VERSION
        0,                        # EI_OSABI
        0,                        # EI_ABIVERSION
        0, 0, 0, 0, 0, 0, 0, 0   # EI_PAD: 8 bytes padding
    ]
    
    # ELF Header (64-bit) - 64 bytes total
    # Using native struct for proper packing
    header = bytearray(64)
    header[0:16] = e_ident
    
    # e_type (2 bytes at offset 16)
    struct.pack_into('<H', header, 16, 2)      # ET_EXEC
    # e_machine (2 bytes at offset 18)
    struct.pack_into('<H', header, 18, 0x3E)  # EM_X86_64
    # e_version (4 bytes at offset 20)
    struct.pack_into('<I', header, 20, 1)
    # e_entry (8 bytes at offset 24)
    struct.pack_into('<Q', header, 24, 0x400100)
    # e_phoff (8 bytes at offset 32) - program header offset
    struct.pack_into('<Q', header, 32, 64)
    # e_shoff (8 bytes at offset 40) - section header offset
    struct.pack_into('<Q', header, 40, 0)
    # e_flags (4 bytes at offset 48)
    struct.pack_into('<I', header, 48, 0)
    # e_ehsize (2 bytes at offset 52)
    struct.pack_into('<H', header, 52, 64)
    # e_phentsize (2 bytes at offset 54)
    struct.pack_into('<H', header, 54, 56)
    # e_phnum (2 bytes at offset 56)
    struct.pack_into('<H', header, 56, 1)
    # e_shentsize (2 bytes at offset 58)
    struct.pack_into('<H', header, 58, 0)
    # e_shnum (2 bytes at offset 60)
    struct.pack_into('<H', header, 60, 0)
    # e_shstrndx (2 bytes at offset 62)
    struct.pack_into('<H', header, 62, 0)
    
    # Program Header (56 bytes) - PT_LOAD
    phdr = bytearray(56)
    struct.pack_into('<I', phdr, 0, 1)           # p_type: PT_LOAD
    struct.pack_into('<I', phdr, 4, 7)           # p_flags: rwx
    struct.pack_into('<Q', phdr, 8, 0)           # p_offset
    struct.pack_into('<Q', phdr, 16, 0x400000)   # p_vaddr
    struct.pack_into('<Q', phdr, 24, 0x400000)   # p_paddr
    struct.pack_into('<Q', phdr, 32, 0x1000)     # p_filesz
    struct.pack_into('<Q', phdr, 40, 0x1000)     # p_memsz
    struct.pack_into('<Q', phdr, 48, 0x1000)     # p_align
    
    # .text section content (simple NOPs)
    text_content = b'\x90' * 256
    
    # Build the ELF file
    with open(output_path, 'wb') as f:
        f.write(header)
        f.write(phdr)
        # Padding to reach 0x400000
        f.write(b'\x00' * (0x400000 - f.tell()))
        f.write(text_content)
    
    print(f"Created simple ELF at: {output_path}")
    return True


if __name__ == '__main__':
    output = r'F:\filebin\test-elf\testfile.elf'
    create_simple_elf(output)