#!/bin/bash

echo "Grab Eurocontrol XLS"
wget http://www.eurocontrol.int/rmalive/regulatorExport.do?type=xls -O data/euroc.xls
