# dump1090curses
display dump1090 data in a curses window 

Main python script is `radar.pl` supported by class `plane.py`, other scripts/files 
are just part of the evolution and tests.

## setup
Create virtual environment and install requirements:
```
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

## usage
Run the curses radar display:
```
source venv/bin/activate
python3 scripts/run_radar.py
```

