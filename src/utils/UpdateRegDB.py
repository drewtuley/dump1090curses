#! /usr/bin/python

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__ = "andrew.tuley"
__date__ = "$06-May-2015 15:17:29$"

import sqlite3
import tomllib

if __name__ == "__main__":
    with open ("config.toml", "rb") as f:
        config = tomllib.load(f)
        
        db_filename = config['directories']['data']+'/'+config['database']['dbname']
        schema_filename = 'src/utils/RegDBSetup.sql'
            

        with sqlite3.connect(db_filename) as conn:      
            print ('Creating/Updating schema: '+schema_filename)
            with open(schema_filename, 'rt') as f:
                schema = f.read()
                conn.executescript(schema)
            
            print ('Adding location data')
            locations = {'LBA':(53.8736961, -1.6732249), 'Leeds':(53.797365, -1.5580089), 
            'Harrogate':(53.9771475, -1.5430934), 'Skipton':(53.9552364, -2.0219937), 
            'Bradford':(53.7470237, -1.728551), 'Sheffield':(53.3957166, -1.4994562), 
            'Hawes':(54.3040185, -2.198943), 'Doncaster':(53.5188469, -1.1200236), 
            'Wakefield':(53.6782581, -1.3712726), 'Manc-EGCC':(53.2114, -2.1630)}
            
            crsr = conn.cursor()
            for loc in locations:
                sql='insert into location select "'+loc+'",'+str(locations[loc][0])+','+str(locations[loc][1])
                print (sql)
                crsr.execute(sql)
                
            conn.commit()
