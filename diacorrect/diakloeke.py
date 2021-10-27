"""
Correct the Excel WGD file

This version created by Erwin R. Komen
Date: 29/oct/2020

Example:
    python diakloeke.py 
        -i "D:/Data Files/TG/Dialecten/data/2020/dsdd_keywords_0.json" 
        -o "D:/Data Files/TG/Dialecten/data/2020/dsdd_kloeke_0.json"

"""

import sys, getopt, os.path, importlib
import io, sys, os
import json

# /Data Files/TG/Dialecten/data/2020

# My own stuff
from utils import ErrHandle

# Make available error handling
errHandle = ErrHandle()

# ----------------------------------------------------------------------------------
# Name :    main
# Goal :    Main body of the function
# History:
# 29/oct/2020    ERK Created
# ----------------------------------------------------------------------------------
def main(prgName, argv) :
    flInput = ''        # input file name: XML with author definitions
    flOutput = ''       # output file name
    readonly = True

    try:
        sSyntax = prgName + ' -i <JSON DSDD file> -o <output JSON file> [-w]'
        # get all the arguments
        try:
            # Get arguments and options
            opts, args = getopt.getopt(argv, "hi:o:w", ["-ifile=", "-ofile"])
        except getopt.GetoptError:
            print(sSyntax)
            sys.exit(2)
        # Walk all the arguments
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print(sSyntax)
                sys.exit(0)
            elif opt in ("-i", "--ifile"):
                flInput = arg
            elif opt in ("-o", "--ofile"):
                flOutput = arg
            elif opt in ("-w", "--write"):
                readonly = False
        # Check if all arguments are there
        if (flInput == '' or flOutput == ''):
            errHandle.DoError(sSyntax)

        # Continue with the program
        errHandle.Status('Input is "' + flInput + '"')
        errHandle.Status('Output is "' + flOutput + '"')

        # Call the function that does the job
        oArgs = dict(input=flInput, output=flOutput, readonly=readonly)
        if (not do_dialect_kloeke(oArgs)) :
            errHandle.DoError("Could not complete")
            return False
        
            # All went fine    
        errHandle.Status("Ready")
    except:
        # act
        errHandle.DoError("main")
        return False

# ----------------------------------------------------------------------------------
# Name :    do_dialect_kloeke
# Goal :    Retrieve list of kloeke-to-coordinate
# History:
# 29/oct/2020    ERK Created
# ----------------------------------------------------------------------------------
def do_dialect_kloeke(oArgs):
    """Perfrom dialect correction"""

    # Defaults
    flInput = ""
    flOutput = ""
    lAuthor = []
    read_only = True

    count = 0
    try:
        # Recover the arguments
        if "input" in oArgs: flInput = oArgs["input"]
        if "output" in oArgs: flOutput = oArgs["output"]
        if "readonly" in oArgs: read_only = oArgs["readonly"]

        # Check input file
        if not os.path.isfile(flInput):
            errHandle.Status("Please specify an input FILE")
            return False

        # Read the input file into a python object
        with open(flInput, "r", encoding="utf-8") as fd:
            data = json.load(fd)

        kloekecodes = []
        kloekeinfos = []

        # Walk all keywords data
        for keyword in data['keywords']:
            if keyword['data.count'] > 0:
                for result in keyword['data']:
                    # Get at least the kloeke
                    kloeke = result['kloeke']
                    if not kloeke in kloekecodes:
                        kloekecodes.append(kloeke)
                        dictionary = result['dictionary']
                        country = result['country']
                        province = result['province']
                        place = result['place']
                        point = result['point']
                        oKloeke = dict(kloeke=kloeke, dictionary=dictionary, country=country, province=province,
                                       place=place, point=point)
                        kloekeinfos.append(oKloeke)

        # Sort the list
        info_sorted = sorted(kloekeinfos, key=lambda x: x['kloeke'] )
        # Write the list of codes
        with open(flOutput, "w", encoding="utf-8") as fd:
            json.dump(info_sorted, fd, indent=2)

        # Return positively
        return True
    except:
        sMsg = errHandle.get_error_message()
        errHandle.DoError("do_dialect_kloeke")
        return False




# ----------------------------------------------------------------------------------
# Goal :    If user calls this as main, then follow up on it
# ----------------------------------------------------------------------------------
if __name__ == "__main__":
    # Call the main function with two arguments: program name + remainder
    main(sys.argv[0], sys.argv[1:])
