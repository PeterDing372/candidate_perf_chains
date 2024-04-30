#!/bin/bash

# <---------- Check and Install Python 3.5+ ---------->

if ! command -v python3 &>/dev/null; then
    # Install Python 3 if not present
    sudo apt install python3 -y
fi

# <---------- Install protobuf-compiler and protobuf Python package ---------->

wget https://github.com/protocolbuffers/protobuf/releases/download/v3.19.0/protoc-3.19.0-linux-x86_64.zip
unzip -o -d protoc-3.19.0-linux-x86_64 protoc-3.19.0-linux-x86_64.zip
sudo mv protoc-3.19.0-linux-x86_64/bin/protoc /usr/bin/
pip install google-cloud
pip install google-cloud-vision


# <---------- Check if protobuf-compiler is installed ---------->

# protoc --version

#  <---------- Install Seaborn ---------->

pip install seaborn

# <---------- Download and Install Go ---------->

# Go is a programming language used for various development purposes
if ! command -v go &>/dev/null; then
    wget https://go.dev/dl/go1.20.3.linux-amd64.tar.gz
    sudo tar -C /usr/local -xzf go1.20.3.linux-amd64.tar.gz
    export PATH=$PATH:/usr/local/go/bin
    source ~/.bashrc
    rm go1.20.3.linux-amd64.tar.gz

    # <---------- Check if Go is installed ---------->

    # go version
fi

# Install pprof using go get
go install github.com/google/pprof@latest
# export PATH=$PATH:$HOME/go/bin
export GOPATH=/users/deepmish/perf_chains/go

# Install Bazel

wget https://github.com/bazelbuild/bazel/releases/download/7.0.2/bazel-7.0.2-linux-x86_64
chmod +x bazel-7.0.2-linux-x86_64
sudo mv bazel-7.0.2-linux-x86_64 /usr/local/bin/bazel

# <---------- Check if Bazel is installed ---------->
# bazel --version

# <---------- Install perf_data_converter ---------->

sudo apt-get -y install g++ git libelf-dev libcap-dev
git clone https://github.com/google/perf_data_converter.git
cd perf_data_converter

# Make the .bazelrc file writable by the current user
chmod +x .bazelrc

# Change ownership of .bazelrc to the current user
sudo chown $USER .bazelrc

# Build perf_to_profile using Bazel
sudo bazel build src:perf_to_profile

# Check if the build fails due to an unrecognized option
if [ $? -ne 0 ]; then
    echo "Build failed. Removing the problematic line from .bazelrc."

    # Remove the line containing --noenable_bzlmod
    sed -i '/--noenable_bzlmod/d' .bazelrc
    
    # Retry the build
    sudo bazel build src:perf_to_profile
fi

cd src
sudo bazel build quipper:perf_converter
cd ..
sudo cp bazel-bin/src/quipper/perf_converter /usr/local/bin/
sudo cp bazel-bin/src/perf_to_profile /usr/local/bin/

echo "Setup complete!"
