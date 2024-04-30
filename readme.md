# Perf Chains Tool

## Overview

This tool facilitates the analysis and generation of microarchitectural statistics (CPU cycles) using `perf` and related utilities. Follow the steps below to set up and utilize the tool effectively.

To measure microarchitectural statistics, Perf requires the `PID` as an argument. Follow the steps below to obtain it.

```bash

## Step 1: Identify Task ID - Run this on the master node

# List Docker services to find the task id of the microservice you want to profile
sudo docker service ls

## Step 2: Identify Node

sudo docker service ps <task-id-of-the-microservice>

# Identify the node number and SSH into it 

## Step 3: Obtain Container ID

# List running containers to identify the container ID of the microservice of interest
sudo docker ps

# Identify the container ID of the microservice of interest.

# Use docker inspect to get the PID of the container
docker inspect --format '{{.State.Pid}}' <container-id>

# This command returns the PID. Use this PID to perform monitoring by passing it to Perf.

# Record microarchitectural statistics (CPU cycles) for 60 seconds
# Note: Deviating from this syntax may lead to errors.
sudo perf record -j any_call,any_ret -p <microservice_pid> -- sleep <time_in_seconds>


# The output is written to a file called perf.data. Add any necessary comments as required.
```


## Tool Usage Instructions

1. **Copy perf.data:**
   Place the `perf.data` output file into the `perf_chains/` directory.

2. **Make setup.sh Executable:**
   Navigate to the `perf_chains/` directory and execute the following command to make the setup script executable:
   ```bash
   sudo chmod +x setup.sh
   ```
3. **Install Dependencies:**
    Run the setup script to install the necessary dependencies:
     ```bash
    ./setup.sh
   ```
4. **Update Symbolizer Path:**
    Adjust the path in symbolizer.py to include the location of your pprof. Export the updated path.
   
5. **Set Permissions for perf.data:**
    Ensure appropriate permissions for perf.data:
    ```bash
   sudo chmod +rx perf.data
    ```

7. **Generate Proto File:**
    Execute the following command to generate a proto file:
      ```bash
     sudo perf_converter -i perf.data -o perf.proto -O proto
      ```

8. **Recompile Proto (if needed):**
    If you encounter issues with proto message parsing, recompile the proto with the following commands:
    ```bash
    protoc --python_out=. ./profile.proto
    protoc --python_out=. ./perf_data.proto

    ```
9. **Generate Graphs:**
    Execute the following command to generate the output graphs for the collected samples in the results folder. To make changes to the          graph, modify driver.py:

   ```bash
   sudo python3 driver.py
   ```

## Caution: Empty Lines in Bucketization Files

Ensure that none of the bucketization files used for categorizing functions contain empty lines. Empty lines in these files can lead to discrepancies in the results, as they may cause functions to be categorized incorrectly or not categorized at all. Before using the bucketization files, review them to remove any empty lines.

