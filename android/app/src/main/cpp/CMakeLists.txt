cmake_minimum_required(VERSION 3.22.1)
project(downhill_bridge LANGUAGES CXX)
add_library(downhill_bridge SHARED bridge.cpp mips_sample.cpp)
target_compile_features(downhill_bridge PRIVATE cxx_std_17)
