#!/bin/bash
test_id=$1
here_dir=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
test_dir="${here_dir}/test"
executable="${here_dir}/source/gcd"

case $test_id in
  p1)
    "${executable}" 1071 1029 |& diff "${test_dir}/output.1071.1029" - &> /dev/null && exit 0;;
  p2)
    "${executable}" 555 666 |& diff "${test_dir}/output.555.666" - &> /dev/null && exit 0;;
  p3)
    "${executable}" 678 987 |& diff "${test_dir}/output.678.987" - &> /dev/null && exit 0;;
  p4)
    "${executable}" 8767 653 |& diff "${test_dir}/output.8767.653" - &> /dev/null && exit 0;;
  p5)
    "${executable}" 16777216 512 |& diff "${test_dir}/output.16777216.512" - &> /dev/null && exit 0;;
  p6)
    "${executable}" 16 4 |& diff "${test_dir}/output.16.4" - &> /dev/null && exit 0;;
  p7)
    "${executable}" 315 831 |& diff "${test_dir}/output.315.831" - &> /dev/null && exit 0;;
  p8)
    "${executable}" 513332 91583315 |& diff "${test_dir}/output.513332.91583315" - &> /dev/null && exit 0;;
  p9)
    "${executable}" 112 135 |& diff "${test_dir}/output.112.135" - &> /dev/null && exit 0;;
  p10)
    "${executable}" 310 55 |& diff "${test_dir}/output.310.55" - &> /dev/null && exit 0;;
  n1)
    "${executable}" 0 55 |& diff "${test_dir}/output.0.55" - &> /dev/null && exit 0;;
esac
exit 1
