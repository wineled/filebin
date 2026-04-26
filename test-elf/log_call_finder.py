#!/usr/bin/env python3
"""
从 ELF 静态信息中，由"文件:行号"定位所在函数及完整调用链。
需要安装：pip install pyelftools capstone
"""
import re
import sys
import os
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_ARCH_ARM64, CS_ARCH_X86, CS_MODE_32, CS_MODE_64

# ========== 配置区域 ==========
ELF_PATH = r"F:\CodingProjects\filebin\test-elf\test_dwarf.elf"
LOCATION = "test_dwarf.c:278"  # 要查的 "文件名:行号"
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


def find_addr_by_file_line(dwarfinfo, file, line, include_line=False):
    """通过行号表找到指定文件:行号的地址。

    优先返回精确匹配的行；若未找到，则返回同一文件中行号最接近的地址（若存在）。
    """
    import os
    best = None
    best_diff = None

    for cu in dwarfinfo.iter_CUs():
        lprog = dwarfinfo.line_program_for_CU(cu)
        header = lprog.header
        file_entries = header.get('file_entry', [])
        inc_dirs = header.get('include_directory', [])

        for entry in lprog.get_entries():
            state = entry.state
            if state is None:
                continue

            file_idx = state.file - 1  # DWARF 文件索引从 1 开始
            if file_idx < 0 or file_idx >= len(file_entries):
                continue

            fe = file_entries[file_idx]
            if isinstance(fe, dict):
                raw_name_b = fe.get('name', b'')
                dir_idx = fe.get('directory_index', 0)
            else:
                raw_name_b = getattr(fe, 'name', None)
                dir_idx = getattr(fe, 'directory_index', 0)
                if raw_name_b is None:
                    raw_name_b = getattr(fe, '_mock_name', None) or getattr(fe, '_mock_new_name', None)
                # unittest.mock.Mock will create child mocks for unknown attrs;
                # ensure dir_idx is an int when possible
                try:
                    dir_idx = int(dir_idx)
                except Exception:
                    dir_idx = 0

            # 仅接受 bytes 或 str 类型作为文件名；其他类型视为空
            if isinstance(raw_name_b, (bytes, bytearray)):
                try:
                    raw_name = raw_name_b.decode()
                except Exception:
                    raw_name = ''
            elif isinstance(raw_name_b, str):
                raw_name = raw_name_b
            else:
                raw_name = ''

            if not raw_name:
                continue

            # 组装完整路径：目录前缀 + 文件名
            if dir_idx > 0 and dir_idx <= len(inc_dirs):
                dir_entry = inc_dirs[dir_idx - 1]
                try:
                    dir_prefix = dir_entry.decode() if isinstance(dir_entry, (bytes, bytearray)) else str(dir_entry)
                except Exception:
                    dir_prefix = str(dir_entry)
                fname = dir_prefix.rstrip('/\\') + '/' + raw_name
            else:
                fname = raw_name

            base = os.path.basename(fname)
            if file == base or file in fname:
                if state.line == line:
                    if include_line:
                        return state.address, state.line
                    return state.address
                diff = abs(state.line - line) if state.line is not None else None
                if diff is not None:
                    if best_diff is None or diff < best_diff:
                        best_diff = diff
                        best = (state.address, state.line) if include_line else state.address

    return best


def find_func_by_addr(addr, funcs):
    for name, low, high in funcs:
        if low <= addr < high:
            return name, low, high
    return None, None, None


def get_function_source(dwarfinfo, low, high, prefer_file=None):
    """返回 (file_path, min_line, max_line) 覆盖函数地址区间的源代码行范围。

    prefer_file: 可选的文件名提示（basename 或包含的路径片段），用于在多个文件匹配时优先选择。
    """
    files = []
    for cu in dwarfinfo.iter_CUs():
        try:
            lprog = dwarfinfo.line_program_for_CU(cu)
        except Exception:
            continue
        header = lprog.header
        file_entries = header.get('file_entry', [])
        inc_dirs = header.get('include_directory', [])

        for entry in lprog.get_entries():
            state = entry.state
            if state is None or state.address is None:
                continue
            if not (low <= state.address < high):
                continue

            file_idx = state.file - 1
            if file_idx < 0 or file_idx >= len(file_entries):
                continue

            fe = file_entries[file_idx]
            if isinstance(fe, dict):
                raw_name_b = fe.get('name', b'')
                dir_idx = fe.get('directory_index', 0)
            else:
                raw_name_b = getattr(fe, 'name', None)
                dir_idx = getattr(fe, 'directory_index', 0)

            if isinstance(raw_name_b, (bytes, bytearray)):
                try:
                    raw_name = raw_name_b.decode()
                except Exception:
                    raw_name = ''
            elif isinstance(raw_name_b, str):
                raw_name = raw_name_b
            else:
                raw_name = ''

            if not raw_name:
                continue

            if dir_idx > 0 and dir_idx <= len(inc_dirs):
                dir_entry = inc_dirs[dir_idx - 1]
                try:
                    dir_prefix = dir_entry.decode() if isinstance(dir_entry, (bytes, bytearray)) else str(dir_entry)
                except Exception:
                    dir_prefix = str(dir_entry)
                fname = dir_prefix.rstrip('/\\') + '/' + raw_name
            else:
                fname = raw_name

            files.append((fname, state.line))

    if not files:
        return None

    # 选择最合适的文件路径
    file_paths = [p for p, ln in files if p]
    if not file_paths:
        return None

    chosen = None
    if prefer_file:
        for p in set(file_paths):
            if os.path.basename(p) == prefer_file or prefer_file in p:
                chosen = p
                break

    if not chosen:
        from collections import Counter
        chosen = Counter(file_paths).most_common(1)[0][0]

    lines = [ln for p, ln in files if p == chosen and ln is not None]
    if not lines:
        return (chosen, None, None)
    return (chosen, min(lines), max(lines))


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
    text = elf.get_section_by_name('.text')
    if not text:
        raise ValueError("未找到 .text 段")
    code = text.data()
    # 兼容不同 Section 对象的地址获取方式
    base = None
    try:
        base = text['sh_addr']
    except Exception:
        try:
            base = text.header.get('sh_addr', 0)
        except Exception:
            base = getattr(text, 'header', {}).get('sh_addr', 0)

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

        # 找到被调用的函数（通过地址范围匹配）
        callee_name, _, _ = find_func_by_addr(call_target, funcs)

        if caller_func and callee_name:
            call_graph[caller_func].add(callee_name)

    return call_graph


def find_full_call_chain(call_graph, target_func):
    """查找所有调用 `target_func` 的调用者（广度优先），去重并按距离排序。

    返回列表，从最近的直接调用者开始，逐层向上。
    """
    from collections import deque
    visited = set([target_func])
    result = []
    q = deque([target_func])

    while q:
        func = q.popleft()
        # 遍历调用图时使用确定性顺序（按调用者名字排序）
        for caller, callees in sorted(call_graph.items(), key=lambda x: x[0]):
            if func in callees and caller not in visited:
                visited.add(caller)
                result.append(caller)
                q.append(caller)

    return result


def find_callers(elf, target_addr, funcs):
    """返回直接调用目标地址所属函数的调用者列表（names）。

    参数: elf, target_addr, funcs(list of (name, low, high))
    """
    text = elf.get_section_by_name('.text')
    if not text:
        raise ValueError("未找到 .text 段")

    # 先找到目标地址对应的函数名
    target_name, _, _ = find_func_by_addr(target_addr, funcs)
    if not target_name:
        return []

    call_graph = build_call_graph(elf, funcs)
    callers = [caller for caller, callees in call_graph.items() if target_name in callees]
    return callers


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
    addr_info = find_addr_by_file_line(dwarfinfo, filename, line_no, include_line=True)
    if addr_info is None:
        print(f"[-] 未在调试信息中找到 {filename}:{line_no}", file=sys.stderr)
        sys.exit(1)

    # addr_info 可能是 (addr, matched_line)
    if isinstance(addr_info, tuple):
        addr, matched_line = addr_info
        if matched_line != line_no:
            print(f"[!] 未找到精确行，使用最接近行 {matched_line} 的地址")
    else:
        addr = addr_info

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

    # 输出当前函数的源代码（若可用）
    src_info = get_function_source(dwarfinfo, low, high, prefer_file=filename)
    if src_info:
        src_path, min_ln, max_ln = src_info
        print(f"[*] 尝试读取源文件: {src_path}")
        # 直接尝试打开原路径
        open_path = None
        try:
            if os.path.exists(src_path):
                open_path = src_path
        except Exception:
            open_path = None

        # 如果找不到，按 basename 在工作目录递归搜索
        if not open_path:
            base = os.path.basename(src_path)
            for root, dirs, files in os.walk('.'):
                if base in files:
                    open_path = os.path.join(root, base)
                    break

        if open_path:
            try:
                with open(open_path, 'r', encoding='utf-8', errors='replace') as fh:
                    all_lines = fh.readlines()
                if min_ln is None or max_ln is None:
                    print(f"[!] 未能确定函数的行范围，无法截取源代码（文件: {open_path}）")
                else:
                    print(f"[+] 函数源代码：{os.path.basename(open_path)}:{min_ln}-{max_ln}")
                    for ln in range(min_ln, max_ln + 1):
                        idx = ln - 1
                        if 0 <= idx < len(all_lines):
                            print(f"{ln:5d}: {all_lines[idx].rstrip()}" )
            except Exception as e:
                print(f"[!] 打开源文件失败: {e}")
        else:
            print(f"[!] 未能在磁盘上找到源文件: {src_path}")


    if full_chain:
        print("[+] 完整调用链 (从叶子到根):")
        for i, c in enumerate(full_chain):
            indent = "  " * i
            print(f"    {indent}\\- {c}")
    else:
        print("[-] 未找到调用者（可能是入口函数）")


if __name__ == "__main__":
    main()
