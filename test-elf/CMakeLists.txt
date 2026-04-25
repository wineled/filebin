cmake_minimum_required(VERSION 3.10)
project(test-log-elf CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Default to native build; override with -DCMAKE_TOOLCHAIN_FILE for cross-compile
add_executable(testfile student.cpp)

# Ensure debug symbols are included
target_compile_options(testfile PRIVATE -g -O0)
