import subprocess
import tempfile
import gzip
import profile_pb2
import glob
import os
import functools

pprof_location = "/users/quanched/go/bin/pprof"

def get_pprof_proto(
    perf_data_file,
    pprof_extra_argv=[]
):
    with tempfile.TemporaryDirectory() as tmp_dir:
        pprof_command = [pprof_location,
                        "-proto",
                        "-output",
                        f"{tmp_dir}/pprof.pb.gz",
                        perf_data_file
                        ] + pprof_extra_argv
        print("generating profile")
        pprof_res = subprocess.run(pprof_command, capture_output=True)
        # print(pprof_res)
        if pprof_res.returncode != 0:
            print("Error generating pprof output")
            print(pprof_res.stderr)
            return None
        with open(f"{tmp_dir}/pprof.pb.gz", "rb") as zipped_file:
            unzipped = gzip.GzipFile(fileobj=zipped_file).read()
            return profile_pb2.Profile().FromString(unzipped)


class SymbolLookupRange:
    
    def __init__(
        self,
        memory_start,
        memory_limit,
        file_offset,
        build_id
    ):
        self.memory_start = memory_start
        self.memory_limit = memory_limit
        self.file_offset = file_offset
        self.build_id = build_id
    def get_binary_addr(self, address):

        if self.memory_start == 0 and address >= self.file_offset:
            return address - self.file_offset
        else:
            return address - self.memory_start + self.file_offset

def get_symbol_lookup_ranges(perf_data_file):
    pprof_proto = get_pprof_proto(perf_data_file)

    if pprof_proto:
        symbol_lookup_ranges = []

        # Extract pprof mapping table
        for m in pprof_proto.mapping:
            if not pprof_proto.string_table[m.build_id]:
                continue
            
            symbol_lookup_ranges.append(
                SymbolLookupRange(
                    m.memory_start,
                    m.memory_limit,
                    m.file_offset,
                    pprof_proto.string_table[m.build_id]
                )
            )
        return symbol_lookup_ranges
    else:
        return None

class Symbolizer:

    def __init__(self, perf_data_file):
        self.perf_data_file = perf_data_file
        self.symbol_lookup_ranges = get_symbol_lookup_ranges(self.perf_data_file)
    
    @functools.lru_cache(maxsize=None)
    def get_symbols(
        self, addr
    ):
        in_addr=addr
        bin_addr_rmap = {}
        build_id_to_addr_map = {}
        for slr in self.symbol_lookup_ranges:
            if addr >= slr.memory_start and addr < slr.memory_limit:
                if slr.build_id not in build_id_to_addr_map:
                    build_id_to_addr_map[slr.build_id] = []

                bin_addr = slr.get_binary_addr(addr)

                bin_addr_rmap[(slr.build_id, bin_addr)] = addr
                build_id_to_addr_map[slr.build_id].append(bin_addr)
        
        ret = {}
        ret[addr] = None
        
        for build_id, addrs in build_id_to_addr_map.items():
            if not addrs:
                continue
            # print(str(build_id) + ", " + str(addrs))

            # get build_id file
            build_file = os.path.join(
                os.environ["HOME"],
                ".debug",
                ".build-id",
                build_id[0:2],
                build_id[2:],
                "elf"
            )
            # if build_id=="ea81f6db6ec6ab2fb9cbee8a95c9b94ad4bf9f11":
            #     print(addr)
            #     print(in_addr)
            if not os.path.isfile(build_file):
                build_file = os.path.join(
                                os.environ["HOME"],
                                ".debug",
                                ".build-id",
                                build_id[0:2],
                                build_id[2:],
                                "vdso"
                            )
            # print(build_file)

            addr_str = " ".join([hex(addr) for addr in addrs])
            # run addr2line
            base_addr2line_command = [
                "addr2line",
                "-C",
                "-f",
                "-e", build_file,
            ]
            addr2line_command = base_addr2line_command.copy()
            addr2line_command.extend([hex(addr) for addr in addrs])
            addr_res = subprocess.run(addr2line_command, capture_output=True)
            # print(addr_res.stdout.decode())

            lines = addr_res.stdout.decode().split("\n")
            
            symbols = lines[::2]
            # print(symbols)
            if symbols[0] == "??":
                addr2line_command = base_addr2line_command.copy()
                addr2line_command.extend([hex(bin_addr_rmap[(build_id, addr)]) for addr in addrs])
                addr_res = subprocess.run(addr2line_command, capture_output=True)
                lines = addr_res.stdout.decode().split("\n")     
                symbols = lines[::2]  
            for (symbol, addr) in zip(symbols, addrs):
                # if symbol == "??":
                #     print(symbols)
                #     print(f"{build_id}, {addr}, {bin_addr_rmap[(build_id, addr)]}")
                ret[bin_addr_rmap[(build_id, addr)]] = symbol

        return ret

        

# print(get_symbol_lookup_ranges("../perf.data"))

# s = Symbolizer("../perf.data")
# print(s.get_symbols([94378379552526, 94378379512512]))
