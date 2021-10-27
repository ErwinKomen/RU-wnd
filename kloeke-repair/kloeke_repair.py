"""
Repair Kloeke code and City name in an excel

This version created by Erwin R. Komen 
Date: 7/feb/2019
"""
import sys, getopt, os.path, importlib
import os, sys, re
import util, csv, json
import requests
import openpyxl
from openpyxl.styles import colors
from openpyxl.styles import Font, Color
from openpyxl import Workbook

KLOEKE_HOME = "https://e-wgd.nl/api/kloeke"

errHandle = util.ErrHandle()

# ----------------------------------------------------------------------------------
# Name :    main
# Goal :    Main body of the function
# History:
# 7/feb/2019    ERK Created
# ----------------------------------------------------------------------------------
def main(prgName, argv) :
  flInput = ''        # input file name
  flOutput = ''       # output file name

  try:
    sSyntax = prgName + ' -i <input file> -o <output file>'
    # get all the arguments
    try:
      # Get arguments and options
      opts, args = getopt.getopt(argv, "hi:o:", ["-ifile=", "-ofile"])
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
    # Check if all arguments are there
    if (flInput == '' or flOutput == ""):
      errHandle.DoError(sSyntax)

    # Continue with the program
    errHandle.Status('Input is "' + flInput + '"')
    errHandle.Status('Output is "' + flOutput + '"')

    # Call the function that does the job
    oArgs = {'input': flInput,
             'output': flOutput}
    if (not process_excel_kloeke(oArgs)) :
      errHandle.DoError("Could not complete")
      return False
    
      # All went fine  
    errHandle.Status("Ready")
  except:
    # act
    errHandle.DoError("main")
    return False

def get_kloeke(data):
    """Ask the KLOEKE API of wgd"""

    url = KLOEKE_HOME
    oBack = {'status': 'ok'}
    try:
        r = requests.post(url, data=data)
    except:
        oBack['status'] = "error"
        msg = errHandle.get_error_message()
        oBack['html'] = "The KLOEKE server gives an error: {}".format(msg)
        return oBack
    # Action depends on what we receive
    if r.status_code == 200:
        # Convert to JSON
        reply = json.loads(r.text.replace("\t", " "))
        # Check the status of the response
        if reply['status'] == "ok":
            # Get the result
            oResult = reply['result']
            if 'list' in oResult:
                lResults = oResult['list']
                num = len(lResults)
                if num == 0:
                    # No result
                    oBack['status'] = "error"
                    oBack['html'] = "(no result)"
                elif num == 1:
                    oBack['count'] = 1
                    oBack['result'] = lResults[0]
                else:
                    # Take the first one?
                    oBack['result'] = lResults[0]
                    oBack['count'] = num
            else:
                oBack['status'] = "error"
                oBack['html'] = "(no list)"
        else:
            oBack['status'] = "error"
            if 'html' in reply:
                oBack['html'] = "The kloeke server returns: {}".format(reply['html'])
            else:
                oBack['html'] = "The kloeke server returns an error"
    else:
        oBack['status'] = "error"
        oBack['html'] = "The KLOEKE server gives an error: {}".format(r.status_code)

    # Return what we found
    return oBack

# ----------------------------------------------------------------------------------
# Name :    process_excel_kloeke
# Goal :    Convert one Excel file containing kloeke codes and city names
# History:
# 7/feb/2019    ERK Created
# ----------------------------------------------------------------------------------
def process_excel_kloeke(oArgs):
    """Process one Excel file"""

    row_answer = 9      # The column that contains the answer (in JSON)
    row_answer_roman = 0
    row_answer_semantics = 0
    lHeadings = []
    c_kloeke_code = -1    # Column containing the kloeke-code
    c_kloeke_corr = -1    # Column containing the correction
    c_plaats = -1         # Column containing the original stad
    c_plaats_corr = -1    # Column containing the corrected stad
    lCache = []           # Keep track of the last N 
    cache_size = 10       # Max cache size
    re_number = re.compile("^[0-9]+$")

    stad_repair = [
        {'src': 'Aalst',        'stad': 'Aalst',                'kloeke': 'K108a'},
        {'src': 'Alphen',       'stad': 'Alphen',               'kloeke': 'K194p'},
        {'src': 'Balgoy',       'stad': 'Balgoij',              'kloeke': 'L108p'},
        {'src': 'Beesd',        'stad': 'Beesd',                'kloeke': 'K077p'},
        {'src': 'Beneden-Leeuwen', 'stad': 'Beneden-Leeuwen',   'kloeke': 'L053p'},
        {'src': 'Boven-Leeuwen', 'stad': 'Boven-Leeuwen',       'kloeke': 'L053a'},
        {'src': 'Boven-leeuwen', 'stad': 'Boven-Leeuwen',       'kloeke': 'L053a'},
        {'src': 'Bruchem',      'stad': 'Bruchem',              'kloeke': 'K119a'},
        {'src': 'Bruchum',      'stad': 'Bruchem',              'kloeke': 'K119a'},
        {'src': 'Doornenburg',  'stad': 'Doornenburg',          'kloeke': 'L076p'},
        {'src': 'Doornbenburg', 'stad': 'Doornenburg',          'kloeke': 'L076p'},
        {'src': 'Doornenburg/Huissen', 'stad': 'Doornenburg',   'kloeke': 'L076p'},
        {'src': 'Dreumel',      'stad': 'Dreumel',              'kloeke': 'L047p'},
        {'src': 'Dreuemel',     'stad': 'Dreumel',              'kloeke': 'L047p'},
        {'src': 'Ewijk/Winssen', 'stad': 'Ewijk',               'kloeke': 'L064p'},
        {'src': 'Echteld',      'stad': 'Echteld',              'kloeke': 'L049p'},
        {'src': 'Gendt',        'stad': 'Gendt',                'kloeke': 'L070p'},
        {'src': 'Groesbeek',    'stad': 'Groesbeek',            'kloeke': 'L119p'},
        {'src': 'Huissen',      'stad': 'Huissen',              'kloeke': 'L026p'},
        {'src': 'Ingen',        'stad': 'Ingen',                'kloeke': 'L005p'},
        {'src': 'Leerbroek',    'stad': 'Leerbroek',            'kloeke': 'K072p'},
        {'src': 'Maurik',       'stad': 'Maurik',               'kloeke': 'L003p'},
        {'src': 'Milingen a/d Rijn',    'stad': 'Millingen aan de Rijn', 'kloeke': 'L075p'},
        {'src': 'Milingen a.d Rijn',    'stad': 'Millingen aan de Rijn', 'kloeke': 'L075p'},
        {'src': 'Millingen a.d Rijn',    'stad': 'Millingen aan de Rijn', 'kloeke': 'L075p'},
        {'src': 'Millingen',    'stad': 'Millingen aan de Rijn', 'kloeke': 'L075p'},
        {'src': 'Millingen a/d Rijn',    'stad': 'Millingen aan de Rijn', 'kloeke': 'L075p'},
        {'src': 'Ochten',       'stad': 'Ochten',               'kloeke': 'L051p'},
        {'src': 'Ooy',          'stad': 'Ooij',                 'kloeke': 'L033a'},
        {'src': 'Ophemert',     'stad': 'Ophemert',             'kloeke': 'L046p'},
        {'src': 'Opheusden',    'stad': 'Opheusden',            'kloeke': 'L013p'},
        {'src': 'Deest/Puiflijk', 'stad': 'Puiflijk',           'kloeke': 'L054b'},
        {'src': 'Puiflijk/Deest', 'stad': 'Puiflijk',           'kloeke': 'L054b'},
        {'src': 'Spijk',        'stad': 'Spijk',                'kloeke': 'L080a'},
        {'src': 'Tiel',         'stad': 'Tiel',                 'kloeke': 'L144p'},
        {'src': 'Tricht',       'stad': 'Tricht',               'kloeke': 'K079a'},
        {'src': 'Varik',        'stad': 'Varik',                'kloeke': 'L087p'},
        {'src': 'Wychen',       'stad': 'Wijchen',              'kloeke': 'L016p'},
        {'src': 'Zoelmond',     'stad': 'Zoelmond',             'kloeke': 'K040a'},
        {'src': 'åpeldoorn',    'stad': 'Apeldoorn',            'kloeke': 'F151p'},
        {'src': 'Bunschoten-Spakenburg', 'stad': 'Bunschoten',  'kloeke': 'F139p'},
        {'src': 'Deelen',       'stad': 'Woeste Hoeve',         'kloeke': 'F173a'},
        {'src': 'Emst',         'stad': 'Emst',                 'kloeke': 'F129b'},
        {'src': 'Epe',          'stad': 'Epe',                  'kloeke': 'F112p'},
        {'src': 'F 153',        'stad': 'Ugchelen',             'kloeke': 'F153p'},
        {'src': 'Garderen',     'stad': 'Garderen',             'kloeke': 'F145p'},
        {'src': 'Hattem',       'stad': 'Hattem',               'kloeke': 'F103p'},
        {'src': 'Hattemerbroek/Wezep', 'stad': 'Hattemerbroek', 'kloeke': 'F103a'},
        {'src': 'Heerde',       'stad': 'Heerde',               'kloeke': 'F113p'},
        {'src': 'Hoenderloo',   'stad': 'Hoenderloo',           'kloeke': 'F173p'},
        {'src': 'Lieren',       'stad': 'Klarenbeek',           'kloeke': 'F157a'},
        {'src': 'Lunteren',     'stad': 'Lunteren',             'kloeke': 'F171p'},
        {'src': 'Nunspeet',     'stad': 'Nunspeet',             'kloeke': 'F111p'},
        {'src': 'Oene',         'stad': 'Oene',                 'kloeke': 'F115p'},
        {'src': 'Speuld',       'stad': 'Speuld',               'kloeke': 'F125p'},
        {'src': 'Speult',       'stad': 'Speuld',               'kloeke': 'F125p'},
        {'src': 'Terwolde',     'stad': 'Terwolde',             'kloeke': 'F131p'},
        {'src': 'Twello',       'stad': 'Twello',               'kloeke': 'F155p'},
        {'src': 'Ufchelen',     'stad': 'Ugchelen',             'kloeke': 'F153p'},
        {'src': 'Vaassen',      'stad': 'Vaassen',              'kloeke': 'F129p'},
        {'src': 'Vaassen/Epe',  'stad': 'Vaassen',              'kloeke': 'F129p'},
        {'src': 'Veendaal',     'stad': 'Veenendaal',           'kloeke': 'F191p'},
        {'src': 'Voorst',       'stad': 'Voorst',               'kloeke': 'F158p'},
        {'src': 'Wapenv eld',   'stad': 'Wapenveld',            'kloeke': 'F104p'},
        {'src': 'Wapenveld',    'stad': 'Wapenveld',            'kloeke': 'F104p'}
        ]

    try:
        # Recover the arguments
        if "input" in oArgs: flInput = oArgs["input"]
        if "output" in oArgs: flOutput = oArgs["output"]

        # Check input file
        if not os.path.isfile(flInput):
            errHandle.Status("Please specify an input FILE")
            return False

        # Set a warning font color
        ft_warning = Font(color=colors.RED)

        # Open the Excel file
        # wb = openpyxl.load_workbook(flInput, read_only=True)
        wb = openpyxl.load_workbook(flInput)
        # Access the default worksheet
        ws = wb.get_active_sheet()
        # Start an iterator for the rows
        oRows = iter(ws)
        row = 1
        bNamesRead = False
        # Skip rows until we are at the point where the first row starts
        oRow = next(oRows, None)
        while oRow != None:
            if row == 1:
                # This is the top row that contains the column names
                for idx, cell in enumerate(oRow):
                    name = cell.value
                    if name == "kloeke-code":
                        c_kloeke_code = idx
                    elif name == "kloeke-corr":
                        c_kloeke_corr = idx
                    elif name == "bron":
                        c_plaats = idx
                    elif name == "plaats-corr":
                        c_plaats_corr = idx
                if c_kloeke_code >= 0 and c_kloeke_corr >= 0 and c_plaats >= 0 and c_plaats_corr >= 0:
                    bNamesRead = True
            else:
                # This is not the first row, so we can now treat it
                if not bNamesRead:
                    # Cannot go further
                    errHandle.DoError("Cannot find correct header")
                    return False
                lCells = [cell.value for cell in oRow]
                # Other wise we make an initial attempt to correct the plaats and the kloeke
                stad = lCells[c_plaats]
                kloeke_code = lCells[c_kloeke_code]

                # Make sure there is something here
                if stad != None and stad != "" and not isinstance(stad, int) and kloeke_code != None and kloeke_code != "" and not isinstance(kloeke_code, int):
                    # repair the stad name
                    arStad = stad.split("/")
                    # Double check to see if the second part is a number or not
                    if len(arStad) > 1 and re_number.match(arStad[1]):
                        # Second part is a number
                        # Just take the first part before any slash
                        stad = arStad[0].strip()
                    else:
                        # Stad remains what it is
                        stad = stad.strip()
                    stad_save = stad

                    # Get the original kloeke code
                    kloeke = kloeke_code.strip()

                    # Show where we are
                    errHandle.Status("row {}: stad=[{}] code=[{}]".format(row, stad, kloeke))

                    # Check if this is in the cache
                    bFound = False
                    for item in lCache:
                        if item['stad'] == stad and item['kloeke'] == kloeke:
                            # Get it out of the cache
                            bSkip = False
                            stad = item['stad_corr']
                            kloeke = item['kloeke_corr']
                            bFound = True
                            break
                    if not bFound:
                        item = {'stad': stad, 'kloeke': kloeke}
                        # Format should be: <capital letter>$ <digit><digit><digit> [<lower case letter>]
                        k_first = ""
                        k_last = ""
                        k_number = ""
                        bFirst = True
                        for letter in kloeke:
                            if bFirst and letter != " " and not letter.isdigit():
                                k_first = k_first + letter
                            elif letter != " ":
                                bFirst = False
                                if  letter.isdigit():
                                    k_number = k_number + letter
                        # Get the last one
                        if not letter.isdigit():
                            k_last = letter
                        # Reconstruct:
                        # errHandle.Status("first=[{}] number=[{}] last=[{}]".format(k_first, k_number, k_last))
                        kloeke = "{}{:03d}{}".format(k_first, int(k_number), k_last)

                        bSkip = False
                        g_stad = ""
                        g_code = ""

                        # Find the correct 'kloeke' code for this stad
                        oCode = get_kloeke({'stad': stad})
                        if oCode['status'] != "error" and oCode['count'] == 1:
                            g_code = oCode['result']['code']

                        if g_code != "" and g_code.startswith(kloeke):
                            # The kloeke we have needs to be slightly emended
                            kloeke = g_code
                        else:
                            # Look further

                            oStad = get_kloeke({'code': kloeke})
                            if oStad['status'] == "error" or oStad['count'] > 1:
                                # No need to stop, but just be aware
                                g_stad = ""
                            else:
                                g_stad = oStad['result']['stad']
                                # Also get a possibly adapted code
                                g_code = oStad['result']['code']
                            if bSkip:
                                # there was an error with this term, so continue
                                kloeke = "(error)"
                                stad = "(error)"
                            else:

                                if g_stad == "":
                                    # No city has been found -- Try converting from city to kloeke
                                    oCode = get_kloeke({'stad': stad})
                                    if oCode['status'] == "error":
                                        # We cannot find any correspondence...
                                        kloeke = "(none)"
                                        stad = "(none)"
                                    else:
                                        # Set the correct code
                                        kloeke = oCode['result']['code']
                                else:
                                    # Found a city
                                    if g_stad.lower() == stad.lower():
                                        # everything is in order - no adaptation is needed
                                        # Accept where kloeke is not equal to g_code and the latter is not empty
                                        if g_code != "" and kloeke != g_code:
                                            kloeke = g_code
                                    elif g_stad.lower() in stad.lower() or stad.lower() in g_stad.lower():
                                        # This is as good as good: but we need to adapt the city to the one belonging to the kloeke
                                        stad = g_stad
                                        # If kloeke is not equal to g_code and the latter is not empty
                                        if g_code != "" and kloeke != g_code:
                                            kloeke = g_code
                                    else:
                                        # The code points to a different city -- get the correct code
                                        stad = "(none)"
                                        kloeke = "(none)"
                                # Double check none/none situations
                                if stad == "(none)" and kloeke == "(none)":
                                    for oAttempt in stad_repair:
                                        if oAttempt['src'].lower() == stad_save.lower():
                                            stad = oAttempt['stad']
                                            kloeke = oAttempt['kloeke']
                                            break

                        # Add what we have found to the cache
                        item['stad_corr'] = stad
                        item['kloeke_corr'] = kloeke
                        if len(lCache) > cache_size:
                            # Remove one element from the cache
                            lCache.pop(0)
                        # Append item to the cache
                        lCache.append(item)

                    # Add the new values into the Excel
                    if not bSkip:
                        oRow[c_kloeke_corr].value = kloeke
                        oRow[c_plaats_corr].value = stad
                        # Possibly change the color
                        if kloeke == "(none)": oRow[c_kloeke_corr].font = ft_warning
                        if stad == "(none)": oRow[c_plaats_corr].font = ft_warning

            # Go to the next row
            row += 1
            oRow = next(oRows, None)

        # Save it as the output file
        wb.save(flOutput)

        # Return correctly
        return True
    except:
        errHandle.DoError("process_excel_kloeke")
        return False

# ----------------------------------------------------------------------------------
# Goal :  If user calls this as main, then follow up on it
# ----------------------------------------------------------------------------------
if __name__ == "__main__":
  # Call the main function with two arguments: program name + remainder
  main(sys.argv[0], sys.argv[1:])
