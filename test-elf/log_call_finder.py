#!/usr/bin/env python3
"""
从 ELF 静态信息中，由"文件:行号"定位所在函数及完整调用链。
需要安装：pip install pyelftools capstone
"""
import re
import sys
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_ARCH_ARM64, CS_ARCH_X86, CS_MODE_32, CS_MODE_64

# ========== 配置区域 ==========
ELF_PATH = r"F:\CodingProjects\filebin\test-elf\test_dwarf.elf"
LOCATION = "test_dwarf.c:6"  # 要查的 "文件名:行号"
# =============================


def load_elf(path):
    f = open(path, 'rb')
    return ELFFile(f)


def build_function_map(dwarfinfo):
    """返回 list of (name, low_pc, high_pc)"""
    funcs = []
    for cu in dwarfinfo.iter_CUs():
        for die in cu.iter_DIEs():
            if die.tag == 'DW_TAG_subprogram':
                try:
                    name = die.attributes['DW_AT_name'].value.decode()
                except:
                    continue
                low_attr = die.attributes.get('DW_AT_low_pc')
                high_attr = die.attributes.get('DW_AT_high_pc')
                if not low_attr or not high_attr:
                    continue
                low = low_attr.value
                high = high_attr.value
                if high_attr.form in ('DW_FORM_data4', 'DW_FORM_data8', 'DW_FORM_udata'):
                    high = low + high
                funcs.append((name, low, high))
    return funcs


def find_addr_by_file_line(dwarfinfo, file, line):
    """通过行号表找到指定文件:行号的第一个地址"""
    for cu in dwarfinfo.iter_CUs():
        lprog = dwarfinfo.line_program_for_CU(cu)
        header = lprog.header
        files = header.get('file_entry', [])
        for entry in lprog.get_entries():
            state = entry.state
            if state is None:
                continue
            if state.file == 0:
                continue
            file_idx = state.file - 1
            if file_idx < 0 or file_idx >= len(files):
                continue
            fname = files[file_idx].get('name', b'').decode()
            if file in fname and state.line == line:
                return state.address
    return None


def find_func_by_addr(addr, funcs):
    for name, low, high in funcs:
        if low <= addr < high:
            return name, low, high
    return None, None, None


def get_arch_info(elf):
    machine = elf.header['e_machine']
    if machine == 'EM_ARM':
        return CS_ARCH_ARM, CS_MODE_ARM
    elif machine == 'EM_AARCH64':
        return CS_ARCH_ARM64, CS_MODE_ARM
    elif machine == 'EM_386':
        return CS_ARCH_X86, CS_MODE_32
    elif machine == 'EM_X86_64':
        return CS_ARCH_X86, CS_MODE_64
    else:
        raise SystemError(f"不支持的架构: {machine}")


def build_call_graph(elf, funcs):
    """构建调用图：{caller_func: {callee_func1, callee_func2, ...}}"""
    addr_to_func = {low: name for name, low, high in funcs}

    text = elf.get_section_by_name('.text')
    if not text:
        raise ValueError("未找到 .text 段")
    code = text.data()
    base = text['sh_addr']

    arch, mode = get_arch_info(elf)
    md = Cs(arch, mode)
    md.detail = True

    call_graph = {name: set() for name, _, _ in funcs}

    for insn in md.disasm(code, base):
        if arch == CS_ARCH_ARM:
            if insn.mnemonic not in ('bl', 'blx'):
                continue
            if len(insn.operands) > 0 and insn.operands[0].type == 2:
                call_target = insn.operands[0].imm
            else:
                continue
        elif arch == CS_ARCH_ARM64:
            if insn.mnemonic not in ('bl', 'blr'):
                continue
            if len(insn.operands) > 0 and insn.operands[0].type == 2:
                call_target = insn.operands[0].imm
            else:
                continue
        else:  # x86
            if insn.mnemonic != 'call':
                continue
            if len(insn.operands) > 0 and insn.operands[0].type == 2:
                call_target = insn.operands[0].imm
            else:
                continue

        # 找到调用者函数
        caller_func = None
        for name, low, high in funcs:
            if low <= insn.address < high:
                caller_func = name
                break

        # 找到被调用的函数
        callee_func = addr_to_func.get(call_target)

        if caller_func and callee_func:
            call_graph[caller_func].add(callee_func)

    return call_graph


def find_full_call_chain(call_graph, target_func):
    """递归查找完整调用链：所有调用 target_func 的函数及其上游调用者"""
    visited = set()
    result = []

    def dfs(func):
        if func in visited:
            return
        visited.add(func)
        for caller, callees in call_graph.items():
            if func in callees:
                result.append(caller)
                dfs(caller)

    dfs(target_func)
    return result


def main():
    print("[*] 加载 ELF 文件...")
    elf = load_elf(ELF_PATH)
    dwarfinfo = elf.get_dwarf_info()

    if not dwarfinfo.has_debug_info:
        print("[-] ELF 中没有调试信息，无法继续。", file=sys.stderr)
        sys.exit(1)

    print("[*] 构建函数地址映射...")
    funcs = build_function_map(dwarfinfo)
    print(f"    共找到 {len(funcs)} 个函数")

    # 解析文件名和行号
    m = re.match(r'^(.+):(\d+)$', LOCATION)
    if not m:
        print("[-] 位置格式错误，应为 file:line", file=sys.stderr)
        sys.exit(1)
    filename = m.group(1)
    line_no = int(m.group(2))

    print(f"[*] 查找位置 {filename}:{line_no} 对应的地址...")
    addr = find_addr_by_file_line(dwarfinfo, filename, line_no)
    if addr is None:
        print(f"[-] 未在调试信息中找到 {filename}:{line_no}", file=sys.stderr)
        sys.exit(1)

    print(f"    地址: 0x{addr:x}")

    name, low, high = find_func_by_addr(addr, funcs)
    if name is None:
        print("[-] 未找到包含该地址的函数", file=sys.stderr)
        sys.exit(1)

    print(f"[+] 所在函数: {name} (入口 0x{low:x} - 0x{high:x})")

    print("[*] 构建调用图...")
    call_graph = build_call_graph(elf, funcs)

    print("[*] 搜索完整调用链...")
    full_chain = find_full_call_chain(call_graph, name)

    if full_chain:
        print("[+] 完整调用链 (从叶子到根):")
        for i, c in enumerate(full_chain):
            indent = "  " * i
            print(f"    {indent}\\- {c}")
    else:
        print("[-] 未找到调用者（可能是入口函数）")


if __name__ == "__main__":
    main()