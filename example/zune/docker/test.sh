#!/bin/bash
test_id=$1
here_dir=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
test_dir="$here_dir/test"
executable="/experiment/source/zune"

case $test_id in
  p1|p2|p3|p4|p5|p6|p7|p8|p9|p10|p11|p12|p13|p14|p15|p16|p17|p18|n1|n2|n3|n4)
    $executable $(cat $test_dir/$test_id) |& diff $test_dir/output.$test_id - && exit 0;;
esac
exit 1
