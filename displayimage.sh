#!/bin/bash

source "`ueberzug library`"
WIDTH=40
HEIGHT=40

{
    ImageLayer::add [identifier]="example0" [x]=$(($(tput cols)/2-$WIDTH/2)) [y]="0" [path]="$1" [width]="$WIDTH" [height]="$HEIGHT"
	while :
	do
		sleep 1s
	done
} | ImageLayer
