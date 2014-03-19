# For every las file, get its bounding box and insert it into CartoDB
# This could easily be adapter to any other SQL server
# 
# Note that the_geom is in EPSG:4326
# DB structure: the_geom (polygon),lasfile (varchar),processed (bool)

datasrid = 32615
maxinserts = 1000
cartodbname = 'stuporglue'
tablename = 'lidar_bbox'

import sys,os,re,math,glob,subprocess,requests
from subprocess import call
from distutils.spawn import *

if len(sys.argv) != 3:
    print "Usage: lasbbox2sql.py <input directory> <cartodb API key>"
    exit(-1);
else:
    basepath = sys.argv[1]
    cartokey = sys.argv[2]

if find_executable('lasinfo.exe') == None:
    print "Please make sure that lasinfo.exe is in your PATH environment"
    exit(-1)

minline = re.compile('\s*min x y z:\s*(.*)\s+(.*)\s+.*')
maxline = re.compile('\s*max x y z:\s*(.*)\s+(.*)\s+.*')

################ Insert an array into CartoDB
def insertIntoCartoDB(tablerows):
    queryprefix = "INSERT INTO " + tablename + " (lasfile,the_geom) VALUES "
    query = queryprefix + ",".join(tablerows)

    url = 'http://' + cartodbname + '.cartodb.com/api/v2/sql'

    http_header = {
            "Accept" : "text/json",
            "Accept-Language" : "en-us,en;q=0.5",
            "Content-type": "application/x-www-form-urlencoded"
            }

    params = {
            'api_key'   : cartokey,
            'format'    : 'GeoJSON',
            'q'         : query
            }

    params = "q=" + query + "&api_key=" + cartokey

    r = requests.post(url,data=params,headers=http_header)

    print r.status_code
    print r.text

################ Running our functions on input data
# Max and Floor coordinates to the nearest int outwards

tablerows = []

for qdir in glob.glob(basepath + '\\q*'):
    if not os.path.isdir(qdir):
        continue
    print "Processing " + qdir
    for lazfile in glob.glob(qdir + "\\laz\\*.laz"):
        command = "lasinfo.exe -i " + lazfile + " -merged -no_check"
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        output,error = process.communicate()
        returncode = process.poll()

        if error != None:
            print error 
        if returncode != 0:
            print output

        sminx = smaxx = sminy = smaxy = 0
        for line in output.split("\n"):
            matches = minline.match(line.strip())
            if matches:
                sminx = str(int(math.floor(float(matches.group(1)))))
                sminy = str(int(math.floor(float(matches.group(2)))))
            matches = maxline.match(line.strip())
            if matches:
                smaxx = str(int(math.ceil(float(matches.group(1)))))
                smaxy = str(int(math.ceil(float(matches.group(2)))))

        tablerows.append("('" + lazfile + "',"+ "ST_Transform(ST_MakeEnvelope(" + sminx + "," + sminy + "," + smaxx + "," + smaxy + "," + str(datasrid) + "),4326))")

        if len(tablerows) >= maxinserts:
            insertIntoCartoDB(tablerows)
            tablerows = []

if len(tablerows) > 0:
    insertIntoCartoDB(tablerows)

print "Done"