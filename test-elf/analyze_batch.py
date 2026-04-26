#!/usr/bin/env python3
"""批量调用 log_call_finder.analyze_location 并导出 JSON/CSV。

用法示例：
  python analyze_batch.py --elf test_dwarf.elf --locations test_dwarf.c:278 test_dwarf.c:266 --json out.json --csv out.csv
如果不提供 locations，会使用内置示例列表。
"""
import argparse
import json
import csv
import os
from log_call_finder import analyze_location


def run_batch(elf_path, locations, out_json=None, out_csv=None, search_cwd=True):
    results = []
    for loc in locations:
        try:
            res = analyze_location(elf_path, loc, include_line=True, prefer_file=None, search_cwd=search_cwd)
        except Exception as e:
            res = {'error': str(e), 'file': None, 'line': None, 'location': loc}
        # make call_graph JSON serializable
        if 'call_graph' in res and isinstance(res['call_graph'], dict):
            res['call_graph'] = {k: list(v) for k, v in res['call_graph'].items()}
        results.append(res)

    if out_json:
        with open(out_json, 'w', encoding='utf-8') as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
        print(f'Wrote JSON -> {out_json}')

    if out_csv:
        # flatten results into CSV rows
        with open(out_csv, 'w', encoding='utf-8', newline='') as fh:
            writer = csv.writer(fh)
            header = ['location', 'elf_path', 'file', 'line', 'addr', 'matched_line', 'func', 'func_low', 'func_high', 'callers', 'full_chain', 'source_path', 'source_snippet']
            writer.writerow(header)
            for r in results:
                loc = f"{r.get('file') or ''}:{r.get('line') or ''}" if not r.get('file') is None else r.get('location', '')
                addr = f"0x{r['addr']:x}" if r.get('addr') else ''
                callers = ';'.join(r.get('callers') or [])
                full_chain = ';'.join(r.get('full_chain') or [])
                src_path = r.get('source_path') or ''
                snippet = ''
                if r.get('source_lines'):
                    snippet = '\n'.join([f"{ln}:{text}" for ln, text in r['source_lines']])
                writer.writerow([loc, r.get('elf_path',''), r.get('file',''), r.get('line',''), addr, r.get('matched_line',''), r.get('func',''), r.get('func_low',''), r.get('func_high',''), callers, full_chain, src_path, snippet])
        print(f'Wrote CSV -> {out_csv}')

    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--elf', '-e', required=False, default='test_dwarf.elf', help='ELF 文件路径')
    p.add_argument('--locations', '-l', nargs='*', help='位置列表，格式 file:line')
    p.add_argument('--locations-file', '-f', help='包含位置的文件，每行一个 file:line')
    p.add_argument('--discover', '-d', help='从 ELF 的 DWARF 中发现指定源文件的所有行号，参数为源文件名（basename 或部分路径）')
    p.add_argument('--json', help='输出 JSON 文件路径')
    p.add_argument('--csv', help='输出 CSV 文件路径')
    p.add_argument('--no-search-cwd', dest='search_cwd', action='store_false', help='不要在当前工作目录搜索源文件')
    args = p.parse_args()

    locs = []
    if args.locations:
        locs.extend(args.locations)
    if args.locations_file:
        if os.path.exists(args.locations_file):
            with open(args.locations_file, 'r', encoding='utf-8') as fh:
                for line in fh:
                    s = line.strip()
                    if s:
                        locs.append(s)

    if args.discover:
        # 从 ELF DWARF 行表发现所有与指定源文件相关的行号
        from log_call_finder import load_elf
        elf = load_elf(args.elf)
        dwarf = elf.get_dwarf_info()
        found = set()
        for cu in dwarf.iter_CUs():
            try:
                lprog = dwarf.line_program_for_CU(cu)
            except Exception:
                continue
            header = lprog.header
            file_entries = header.get('file_entry', [])
            inc_dirs = header.get('include_directory', [])
            for entry in lprog.get_entries():
                state = entry.state
                if state is None or state.line is None:
                    continue
                file_idx = state.file - 1
                if file_idx < 0 or file_idx >= len(file_entries):
                    continue
                fe = file_entries[file_idx]
                raw_name_b = fe.get('name', b'') if isinstance(fe, dict) else getattr(fe, 'name', None)
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
                # 组装完整路径
                dir_idx = fe.get('directory_index', 0) if isinstance(fe, dict) else getattr(fe, 'directory_index', 0)
                if isinstance(dir_idx, int) and dir_idx > 0 and dir_idx <= len(inc_dirs):
                    dir_entry = inc_dirs[dir_idx - 1]
                    try:
                        dir_prefix = dir_entry.decode() if isinstance(dir_entry, (bytes, bytearray)) else str(dir_entry)
                    except Exception:
                        dir_prefix = str(dir_entry)
                    fname = dir_prefix.rstrip('/\\') + '/' + raw_name
                else:
                    fname = raw_name
                if args.discover in os.path.basename(fname) or args.discover in fname:
                    found.add(state.line)
        locs = [f"{args.discover}:{ln}" for ln in sorted(found)]
        if not locs:
            print(f"未在 DWARF 中发现与 {args.discover} 相关的行。")
    if not locs:
        # 默认示例
        locs = ['test_dwarf.c:278', 'test_dwarf.c:266']

    run_batch(args.elf, locs, out_json=args.json, out_csv=args.csv, search_cwd=args.search_cwd)


if __name__ == '__main__':
    main()
