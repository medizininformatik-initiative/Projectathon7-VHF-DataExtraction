#!/usr/bin/env bash


for file in testdata-input/*.zip
do
    echo $file
    unzip -o "$file" -d testdata
    #rm "$file"
done
