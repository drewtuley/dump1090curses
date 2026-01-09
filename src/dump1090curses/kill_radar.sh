#!/bin/bash

PID=$(ps -fu pi | grep radar.py | grep -v grep | awk '{print $2}')
kill -9 $PID
