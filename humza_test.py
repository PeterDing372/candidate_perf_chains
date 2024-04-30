import symbolizer
import perf_data_pb2
import collections
import seaborn as sns
import matplotlib.pyplot as plt
import functools
import cProfile
import pickle
import numpy as np
import os
from tqdm import tqdm
from copy import deepcopy

def parse_perf_proto(perf_data_proto):
    with open(perf_data_proto, "rb") as proto_file:
        proto_string = proto_file.read()
        perf_data = perf_data_pb2.PerfDataProto().FromString(proto_string)
    return perf_data

def get_events_list(perf_proto):
    return list(filter(lambda event: event.sample_event is not None,
                       perf_proto.events))

PERF_DATA_LOCATION = "./perf.data"
PERF_PROTO_LOCATION = "./perf.proto"

print("Parsing Proto")
perf_proto = parse_perf_proto(PERF_PROTO_LOCATION)
perf_sample_events = get_events_list(perf_proto)

# print("setting up symbolizer")
# symbolize = symbolizer.Symbolizer(PERF_DATA_LOCATION)

if os.path.exists('symbolize.pkl'):
    print('loading symbolize')
    with open('symbolize.pkl', 'rb') as file:
        symbolize = pickle.load(file)    
else:
    print('building symbolize')
    symbolize = symbolizer.Symbolizer(PERF_DATA_LOCATION)
    with open('symbolize.pkl', 'wb') as file:
        pickle.dump(symbolize, file)


def build_ip_mapping(perf_sample_events):
    ip_to_func_name = {}
    for i, event in enumerate(perf_sample_events):
        if i%100 == 0:
            print(f"{i}/{len(perf_sample_events)}")
        sample_event = event.sample_event
        for branch in sample_event.branch_stack:
            if not branch.from_ip in ip_to_func_name:
                # try:
                    ip_to_func_name[branch.from_ip] = symbolize.get_symbols(branch.from_ip)[branch.from_ip]
                # except Exception as err:
                #     ip_to_func_name[branch.from_ip] = "None"
                #     print("Doesn't exist", hex(branch.from_ip))
                    
            if not branch.to_ip in ip_to_func_name:
                # try:
                    ip_to_func_name[branch.to_ip] = symbolize.get_symbols(branch.to_ip)[branch.to_ip]
                # except Exception as err:
                #     ip_to_func_name[branch.to_ip] = "None"
                #     print("Doesn't exist", hex(branch.to_ip))
    return ip_to_func_name


if os.path.exists('ip_to_func_name.pkl'):
    print('loading ip_to_func_name.pkl')
    with open('ip_to_func_name.pkl', 'rb') as file:
        ip_to_func_name = pickle.load(file)    
else:
    print('building ip_to_func_name')
    ip_to_func_name = build_ip_mapping(perf_sample_events)
    with open('ip_to_func_name.pkl', 'wb') as file:
        pickle.dump(ip_to_func_name, file)


# tax_categories = [
#     "c_libraries",
#     "compress",
#     "hash",
#     "encryption",
#     "kernel",
#     "mem",
#     # "miscellaneous",
#     "sync",
#     "rpc",
#     "serialization",
#     "kernel",
#     "application_logic",

# ]

tax_categories = [
    "c_libraries",
    "compress",
    "hash",
    "encryption",
    "kernel",
    "mem",
    # "miscellaneous",
    "sync",
    "rpc",
    "serialization",
    "kernel",
    "application_logic",

]



file_contents = {}

for tax in tax_categories:
    with open(f"bucketization/{tax}_keywords", "r") as f:
        file_contents[tax] = f.readlines()


memo = {}

def bucketize(function_name):
    if function_name in memo:
        return memo[function_name]
    for tax in tax_categories:
        lines = file_contents[tax]
        for func in lines:
            func = func.split("#")[0].strip()
            if func in function_name:
                memo[function_name] = tax
                return tax
    # with open(uncat_file, "a") as uncat:
    #     uncat.write(function_name + "\n")
    memo[function_name] = "application_logic"
    return "application_logic"

def ip_to_bucket(ip):
    function_name = ip_to_func_name[ip]
    bucket = "application_logic"
    if not function_name:
        bucket = "application_logic"
    else:
        bucket = bucketize(function_name)
    return bucket

def funcname_to_bucket(function_name):
    bucket = "application_logic"
    if not function_name:
        bucket = "application_logic"
    else:
        bucket = bucketize(function_name)
    return bucket


functionJumps = {}

functionJumpCounts = {}

func_to_ip = {}

if os.path.exists('functionJumps.pkl') and os.path.exists('functionJumpCounts.pkl') and os.path.exists("func_to_ip.pkl"):
    print('loading functionJumps.pkl and functionJumpCounts.pkl and func_to_ip.pkl')
    with open('functionJumps.pkl', 'rb') as file:
        functionJumps = pickle.load(file)    
    with open('functionJumpCounts.pkl', 'rb') as file:
        functionJumpCounts = pickle.load(file)    
    with open('func_to_ip.pkl', 'rb') as file:
        func_to_ip = pickle.load(file)    
else:
    print('building functionJumps.pkl and functionJumpCounts.pkl and func_to_ip.pkl')
    for i, event in enumerate(tqdm(perf_sample_events)):
        for j, branch in enumerate(event.sample_event.branch_stack):
            
            new_cycles = branch.cycles
            source = ip_to_func_name[branch.from_ip]
            dest = ip_to_func_name[branch.to_ip]
            func_to_ip[source] = hex(branch.from_ip)
            func_to_ip[dest] = hex(branch.to_ip)

            destinations = functionJumps.get(source, {})
            destinations_clockcycles = destinations.get(dest, 0)
            destinations_clockcycles = destinations_clockcycles + new_cycles
            destinations[dest] = destinations_clockcycles
            functionJumps[source] = destinations
            
            source_counts = functionJumpCounts.get(source, {})
            source_counts_dest = source_counts.get(dest, 0)
            source_counts_dest+=1
            source_counts[dest] = source_counts_dest
            functionJumpCounts[source] = source_counts

    
    with open('functionJumps.pkl', 'wb') as file:
        pickle.dump(functionJumps, file)
    with open('functionJumpCounts.pkl', 'wb') as file:
        pickle.dump(functionJumpCounts, file)
    with open('func_to_ip.pkl', 'wb') as file:
        pickle.dump(func_to_ip, file)
    


functionJumpsFractions = deepcopy(functionJumps)
functionJumpTotalCycles = {}

for source in tqdm(functionJumpsFractions):
    total_clock_cycles = 0
    dest_to_cc_mapping = functionJumpsFractions[source]
    for dest in dest_to_cc_mapping:
        total_clock_cycles+=dest_to_cc_mapping[dest]
    functionJumpTotalCycles[source] = total_clock_cycles
    for dest in dest_to_cc_mapping:
        dest_to_cc_mapping[dest]=dest_to_cc_mapping[dest]/total_clock_cycles
    

# make a dictionary with total_clock_cycles threshold
# THRESHOLD_CC = 100000

# for source in functionJumps:
#     if functionJumpTotalCycles[source] < THRESHOLD_CC:
#         del functionJumpsFractions[source]

list_of_jumps = []

for source in functionJumpsFractions:
    for dest in functionJumpsFractions[source]:
        list_of_jumps.append((source, dest, functionJumpsFractions[source][dest], functionJumpTotalCycles[source]*functionJumpsFractions[source][dest]))


list_of_jumps.sort(reverse = True, key = lambda x : x[3])

total_cycles = 0

for source in functionJumpTotalCycles:
    total_cycles+=functionJumpTotalCycles[source]


print("Total number of cycles:", total_cycles)


for i, item in enumerate(list_of_jumps):
    source_bucket = funcname_to_bucket(item[0])
    dest_bucket = funcname_to_bucket(item[1])
    if(source_bucket != dest_bucket or True):
        print(f"{i}: {item}")
        print(f"{source_bucket} -> {dest_bucket}")
        print(f"count: {functionJumpCounts[item[0]][item[1]]}")
        print(f"Average cc/chain = {item[3]/functionJumpCounts[item[0]][item[1]]}")
        # print(func_to_ip[item[0]], func_to_ip[item[1]])

    if i > 2000:
        break
# print(functionJumpsFractions)