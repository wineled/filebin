import pprint
from log_call_finder import analyze_location
res = analyze_location(r'F:/CodingProjects/filebin/test-elf/test_dwarf.elf','test_dwarf.c:278')
# compact call_graph for printing
res['call_graph'] = {k: list(v) for k, v in res['call_graph'].items()}
pp = pprint.PrettyPrinter(indent=2, width=120)
pp.pprint(res)
