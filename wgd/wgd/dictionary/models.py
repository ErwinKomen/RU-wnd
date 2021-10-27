"""Models for the wgd records.

The wgd is the "Dictionary of Limburg Dialects".
Each wgd entry has a gloss, a definition and a number of variants in different dialects.
The dialects are identified by locations, and the locations are indicated by a 'Kloekecode'.

"""
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db import models
from django.db.models import Q
from datetime import datetime
import time
from wgd.settings import APP_PREFIX, MEDIA_ROOT, STATIC_ROOT
from wgd.utils import *
import openpyxl
from openpyxl import Workbook
from openpyxl.utils.cell import get_column_letter
import os, os.path
import sys
import io
import codecs
import html
import json
import csv


MAX_IDENTIFIER_LEN = 10
MAX_LEMMA_LEN = 100
MAX_TITEL_LEN = 255
ENTRY_INDICT = "entry.inwoordenboek"


# ============================= LOCAL CLASSES ======================================
errHandle = ErrHandle()

class FieldChoice(models.Model):

    field = models.CharField(max_length=50)
    english_name = models.CharField(max_length=50)
    dutch_name = models.CharField(max_length=50)
    abbr = models.CharField(max_length=20, default='-')
    machine_value = models.IntegerField(help_text="The actual numeric value stored in the database. Created automatically.")

    def __str__(self):
        return "{}: {}, {} ({})".format(
            self.field, self.english_name, self.dutch_name, str(self.machine_value))

    class Meta:
        ordering = ['field','machine_value']

def get_now_time():
    return time.process_time()

def build_choice_list(field):
    """Create a list of choice-tuples"""

    choice_list = [];
    unique_list = [];   # Check for uniqueness

    try:
        # check if there are any options at all
        if FieldChoice.objects == None:
            # Take a default list
            choice_list = [('0','-'),('1','N/A')]
            unique_list = [('0','-'),('1','N/A')]
        else:
            if maybe_empty:
                choice_list = [('0','-')]
            for choice in FieldChoice.objects.filter(field__iexact=field):
                # Default
                sEngName = ""
                # Any special position??
                if position==None:
                    sEngName = choice.english_name
                elif position=='before':
                    # We only need to take into account anything before a ":" sign
                    sEngName = choice.english_name.split(':',1)[0]
                elif position=='after':
                    if subcat!=None:
                        arName = choice.english_name.partition(':')
                        if len(arName)>1 and arName[0]==subcat:
                            sEngName = arName[2]

                # Sanity check
                if sEngName != "" and not sEngName in unique_list:
                    # Add it to the REAL list
                    choice_list.append((str(choice.machine_value),sEngName));
                    # Add it to the list that checks for uniqueness
                    unique_list.append(sEngName)

            choice_list = sorted(choice_list,key=lambda x: x[1]);
    except:
        print("Unexpected error:", sys.exc_info()[0])
        choice_list = [('0','-'),('1','N/A')];

    # Signbank returns: [('0','-'),('1','N/A')] + choice_list
    # We do not use defaults
    return choice_list;

def build_abbr_list(field, position=None, subcat=None, maybe_empty=False):
    """Create a list of choice-tuples"""

    choice_list = [];
    unique_list = [];   # Check for uniqueness

    try:
        # check if there are any options at all
        if FieldChoice.objects == None:
            # Take a default list
            choice_list = [('0','-'),('1','N/A')]
            unique_list = [('0','-'),('1','N/A')]
        else:
            if maybe_empty:
                choice_list = [('0','-')]
            for choice in FieldChoice.objects.filter(field__iexact=field):
                # Default
                sEngName = ""
                # Any special position??
                if position==None:
                    sEngName = choice.english_name
                elif position=='before':
                    # We only need to take into account anything before a ":" sign
                    sEngName = choice.english_name.split(':',1)[0]
                elif position=='after':
                    if subcat!=None:
                        arName = choice.english_name.partition(':')
                        if len(arName)>1 and arName[0]==subcat:
                            sEngName = arName[2]

                # Sanity check
                if sEngName != "" and not sEngName in unique_list:
                    # Add it to the REAL list
                    choice_list.append((str(choice.abbr),sEngName));
                    # Add it to the list that checks for uniqueness
                    unique_list.append(sEngName)

            choice_list = sorted(choice_list,key=lambda x: x[1]);
    except:
        print("Unexpected error:", sys.exc_info()[0])
        choice_list = [('0','-'),('1','N/A')];

    # Signbank returns: [('0','-'),('1','N/A')] + choice_list
    # We do not use defaults
    return choice_list;

def choice_english(field, num):
    """Get the english name of the field with the indicated machine_number"""

    try:
        result_list = FieldChoice.objects.filter(field__iexact=field).filter(machine_value=num)
        if (result_list == None):
            return "(No results for "+field+" with number="+num
        return result_list[0].english_name
    except:
        return "(empty)"

def choice_value(field, term):
    """Get the numerical value of the field with the indicated English name"""

    try:
        result_list = FieldChoice.objects.filter(field__iexact=field).filter(english_name__iexact=term)
        if result_list == None or result_list.count() == 0:
            # Try looking at abbreviation
            result_list = FieldChoice.objects.filter(field__iexact=field).filter(abbr__iexact=term)
        if result_list == None:
            return -1
        else:
            return result_list[0].machine_value
    except:
        return -1

def choice_abbreviation(field, num):
    """Get the abbreviation of the field with the indicated machine_number"""

    try:
        result_list = FieldChoice.objects.filter(field__iexact=field).filter(machine_value=num)
        if (result_list == None):
            return "{}_{}".format(field, num)
        return result_list[0].abbr
    except:
        return "-"

def m2m_combi(items):
    if items == None:
        sBack = ''
    else:
        qs = items.all()
        sBack = '-'.join([str(thing) for thing in qs])
    return sBack

def m2m_identifier(items):
    if items == None:
        sBack = ''
    else:
        qs = items.all()
        sBack = "-".join([thing.identifier for thing in qs])
    return sBack

def get_ident(qs):
    if qs == None:
        idt = ""
    else:
        lst = qs.all()
        if len(lst) == 0:
            idt = "(empty)"
        else:
            qs = lst[0].entry_set
            idt = m2m_identifier(qs)
    return idt

def int_to_roman(input):
   """Convert an integer to Roman numerals."""
   ints = (1000, 900,  500, 400, 100,  90, 50,  40, 10,  9,   5,  4,   1)
   nums = ('M',  'CM', 'D', 'CD','C', 'XC','L','XL','X','IX','V','IV','I')
   result = ""
   for i in range(len(ints)):
      count = int(input / ints[i])
      result += nums[i] * count
      input -= ints[i] * count
   return result

def isNullOrEmptyOrInt(arPart, lstColumn):
    for iIdx in lstColumn:
        sItem = arPart[iIdx]
        # Check if this item is empty, null or numeric
        if sItem == "" or sItem == "NULL" or sItem.startswith('#') or sItem == "?" or sItem == "-" or sItem.isnumeric():
            # Indicate where the error was
            return iIdx

    # When everything has been checked and there is no indication, return false
    return 0

def isLineOkay(oLine):
    
    try:
        # Validate
        if oLine == None:
            return -1
        # Define which items need to be checked
        lCheck = ['lemma_name', 'trefwoord_name', 'dialectopgave_name', 'dialect_stad', 'dialect_nieuw']
        iIdx = 0
        # Walk all key-value pairs
        for (k,v) in oLine.items():
            iIdx += 1
            # Is this key part of the range that needs checking?
            if k in lCheck:
                # Perform the check here
                if v=="" or v=="NULL" or v.startswith('#') or v=="?" or v=="-" or v.isnumeric():
                    # Indicate where the error was
                    return iIdx

        # When everything has been checked and there is no indication, return false
        return 0
    except:
        sMsg = errHandle.get_error_message()
        errHandle.DoError("isLineOkay", True)
        return -1


# ----------------------------------------------------------------------------------
# Name :    partToLine
# Goal :    Convert an array of values into a structure
# History:
#  12/dec/2016   ERK Created
# ----------------------------------------------------------------------------------
def partToLine(sVersie, arPart, bDoMijnen):
    """Convert an array of values [arPart] into a structure"""

    def get_indexed(arThis, idx):
        """Get the entry, provided arThis is large enough"""
        if arThis != None and len(arThis) - 1 >= idx:
            return arThis[idx]
        else:
            return ""

    k = 0
    v = ""
    offset = 1      # Needed because of [recordId] being first field
    try:
        oBack = {}
        # Preposing of all the parts
        if sVersie == "Lemmanummer":
            oBack['lemma_name'] = arPart[1+offset]             # 1
            oBack['lemma_bronnenlijst'] = arPart[6+offset]     # 6
            oBack['lemma_toelichting'] = arPart[2+offset]      # 2
            oBack['lemma_boek'] = arPart[7+offset]             # 7
            oBack['dialect_stad'] = arPart[10+offset]          # 10
            oBack['dialect_nieuw'] = get_indexed(arPart, 15+offset)    # 15 arPart[15]
            oBack['dialect_kloeke'] = None              # none
            oBack['trefwoord_name'] = arPart[3+offset]         # 3
            oBack['trefwoord_toelichting'] = ""         # empty
            oBack['dialectopgave_name'] = arPart[5+offset]     # 5
            oBack['dialectopgave_toelichting'] = arPart[14+offset]     # 14
            oBack['dialectopgave_kloeketoelichting'] = ""         # See WLD issue #22
        elif sVersie == "lemma.name":
            oBack['lemma_name'] = arPart[0+offset]             # 0
            oBack['lemma_bronnenlijst'] = arPart[2+offset]     # 2
            oBack['lemma_toelichting'] = arPart[1+offset]      # 1
            oBack['lemma_boek'] = ""                    # empty
            oBack['dialect_stad'] = arPart[9+offset]           # 9
            oBack['dialect_nieuw'] = arPart[8+offset]          # 8
            oBack['dialect_kloeke'] = arPart[7+offset]         # 7 - OLD KloekeCode
            oBack['trefwoord_name'] = arPart[3+offset]         # 3
            oBack['trefwoord_toelichting'] = arPart[4+offset]  # 4
            oBack['dialectopgave_name'] = arPart[5+offset]     # 5
            oBack['dialectopgave_toelichting'] = arPart[6+offset]  # 6
            oBack['dialectopgave_kloeketoelichting'] = arPart[10+offset]   # 10 - See WLD issue #22
            # NOTE: part II-5 also contains the names of the mines in [10]

        if sVersie != "":
            # Unescape two items
            oBack['dialectopgave_name'] = html.unescape(oBack['dialectopgave_name'])
            oBack['trefwoord_name'] = html.unescape(oBack['trefwoord_name'])
            # Remove quotation marks everywhere and adapt NULL where needed
            for (k,v) in oBack.items():
                if oBack[k] != None:
                    # Remove leading and trailing quotation marks
                    oBack[k] = v.strip('"')
                    # Remove leading and trailing spaces
                    oBack[k] = oBack[k].strip()
                    # Remove leading and trailing ['] if it is there (on both sides)
                    if oBack[k].startswith("'") and oBack[k].endswith("'"):
                      oBack[k] = oBack[k].strip("'")
                    # Change NULL into space
                    if oBack[k] == "NULL":
                        oBack[k] = ""
                    # Change double "" into single "
                    oBack[k] = oBack[k].replace('""', '"')
            # Need to treat the Mines??
            if bDoMijnen:
                # Check for unknown dialect location
                if oBack['dialect_stad'].lower() == "onbekend":
                    oBack['dialect_stad'] = "Zie mijnen"
                # Get the list of mines
                sMijnen = oBack['dialectopgave_kloeketoelichting'].replace('(', '').replace(')', '').strip()
                # Sanity check
                if sMijnen == "":
                    lMijnen = []
                else:
                    # Adaptations for Oranje nassau mijnen
                    sMijnen = sMijnen.replace('Oranje-Nassau I-IV', 'Oranje-Nassau I / Oranje-Nassau II / Oranje-Nassau III / Oranje-Nassau IV')
                    lMijnen = sMijnen.split('/')
                    # Remove spaces from the mines
                    for i, s in enumerate(lMijnen):
                        s = s.strip()
                        if s == "I": 
                            s = "Oranje-Nassau I"
                        elif s == "II":
                            s = "Oranje-Nassau II"
                        elif s == "III":
                            s = "Oranje-Nassau III"
                        elif s == "IV":
                            s = "Oranje-Nassau IV"
                        lMijnen[i] = s
                    
                # Add the list of Mijnen
                oBack['mijn_list'] = lMijnen

        # Return what we found
        return oBack
    except:
        # Provide more information
        errHandle.Status("partToLine error info [{}]".format(sVersie))
        for idx, val in enumerate(arPart):
            errHandle.Status("arPart[{}] = [{}]".format(idx, val))
        errHandle.Status("partToLine: k={} v={}".format(k, v))
        errHandle.DoError("partToLine", True)
        return None

class HelpChoice(models.Model):
    """Define the URL to link to for the help-text"""
    
    field = models.CharField(max_length=200)        # The 'path' to and including the actual field
    searchable = models.BooleanField(default=False) # Whether this field is searchable or not
    display_name = models.CharField(max_length=50)  # Name between the <a></a> tags
    help_url = models.URLField(default='')          # THe actual help url (if any)

    def __str__(self):
        return "[{}]: {}".format(
            self.field, self.display_name)

    def Text(self):
        help_text = ''
        # is anything available??
        if (self.help_url != ''):
            if self.help_url[:4] == 'http':
                help_text = "See: <a href='{}'>{}</a>".format(
                    self.help_url, self.display_name)
            else:
                help_text = "{} ({})".format(
                    self.display_name, self.help_url)
        return help_text


def get_help(field):
    """Create the 'help_text' for this element"""

    # find the correct instance in the database
    help_text = ""
    try:
        entry_list = HelpChoice.objects.filter(field__iexact=field)
        entry = entry_list[0]
        # Note: only take the first actual instance!!
        help_text = entry.Text()
    except:
        help_text = "Sorry, no help available for " + field

    return help_text


class Information(models.Model):
    """Specific information that needs to be kept in the database"""

    # [1] The key under which this piece of information resides
    name = models.CharField("Key name", max_length=255)
    # [0-1] The value for this piece of information
    kvalue = models.TextField("Key value", default = "", null=True, blank=True)

    class Meta:
        verbose_name_plural = "Information Items"

    def __str__(self):
        return self.name

    def get_kvalue(name):
        info = Information.objects.filter(name=name).first()
        if info == None:
            return ''
        else:
            return info.kvalue

    def set_kvalue(name, value):
        info = Information.objects.filter(name=name).first()
        if info == None:
            info = Information(name=name)
            info.save()
        info.kvalue = value
        info.save()
        return True

    def save(self, force_insert = False, force_update = False, using = None, update_fields = None):
        return super(Information, self).save(force_insert, force_update, using, update_fields)


class Kloeke(models.Model):
    """An overview of all the Kloeke codes and the places they belong to"""

    # [1] The kloeke code itself
    code = models.CharField("Kloekecode", blank=False, max_length=MAX_IDENTIFIER_LEN, default = "-")
    # [1] The main city/village this refers to
    stad = models.CharField("Dialectlocatie", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # [0-1] Old KLOEKE code
    oud = models.CharField("Oude code", blank=True, null=True,max_length=MAX_IDENTIFIER_LEN)
    # [0-1] First alternative
    alt1 = models.CharField("Alternatief 1", blank=True, null=True,max_length=MAX_LEMMA_LEN)
    # [0-1] Second alternative
    alt2 = models.CharField("Alternatief 1", blank=True, null=True,max_length=MAX_LEMMA_LEN)
    # [1] Number of other entries with the same code
    numcode = models.IntegerField("Zelfde code", default=0)
    # [1] Number of other entries with the same stad
    numstad = models.IntegerField("Zelfde stad", default=0)

    def __str__(self):
        return self.code

    def readcodes(fName, oRepair):
        """Read the codes from the indicated file name
        
        NOTE: this does *NOT* yet read the OUD field
        """

        oBack = {}
        oErr = ErrHandle()
        count_add = 0
        count_new = 0
        try:
            # Check existence of file
            if not os.path.exists(fName) or not os.path.isfile(fName):
                oBack['status'] = "error"
                oBack['msg'] = "Cannot find file [{}]".format(fName)
            # Read the file
            with io.open(fName, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f, delimiter='\t')
                lKloeke = list(reader)
            # Now walk the list...
            bFirst = True
            # with transaction.atomic():
            for oKloeke in lKloeke:
                if bFirst:
                    bFirst = False
                else:
                    # Get the parts
                    code = oKloeke[0]
                    stad = oKloeke[1]
                    alt1 = oKloeke[2]
                    alt2 = oKloeke[3]
                    # Obligatory non-empty CODE and STAD
                    if code != "" and stad != "":
                        # Check if the combination exists
                        instance = Kloeke.objects.filter(code=code, stad=stad).first()
                        if instance == None:
                            # First attempt
                            instance = Kloeke(code=code, stad=stad)
                            if alt1 != "": instance.alt1 = alt1
                            if alt2 != "": instance.alt2 = alt2
                            instance.save()
                            count_new += 1
                            oRepair.set_status("New {}, corrected {}".format(count_new, count_add))
                        else:
                            # may be some corrections
                            bNeedSaving = False
                            if instance.alt1 != alt1 and not (instance.alt1 == None and alt1 == ""):
                                instance.alt1 = alt1
                                bNeedSaving = True
                            if instance.alt2 != alt2 and not (instance.alt1 == None and alt1 == ""):
                                instance.alt2 = alt2
                                bNeedSaving = True
                            if instance.alt1 == "":
                                # Change into None
                                instance.alt1 = None
                                bNeedSaving = True
                            if instance.alt2 == "":
                                # Change into None
                                instance.alt2 = None
                                bNeedSaving = True
                            if bNeedSaving:
                                instance.save()
                                count_add += 1
                                oRepair.set_status("New {}, corrected {}".format(count_new, count_add))

            # Second part: count the number of times a city/code occurs
            for instance in Kloeke.objects.all():
                # Count 'code' and 'stad'
                code = instance.code
                stad = instance.stad
                count_code = Kloeke.objects.filter(code=code).count()
                count_stad = Kloeke.objects.filter(stad=stad).count()
                bNeedSaving = False
                # Check if this needs adding
                if instance.numcode != count_code:
                    instance.numcode = count_code
                    bNeedSaving = True
                if instance.numstad != count_stad:
                    instance.numstad = count_stad
                    bNeedSaving = True
                if bNeedSaving:
                    instance.save()
                    oRepair.set_status("Adjusting count of {} / {}".format(code, stad))

            # Success
            oBack['status'] = "ok"
            oBack['msg'] = "Finished. New {}, corrected {}".format(count_new, count_add)
        except:
            oBack['status'] = "error"
            oBack['msg'] = oErr.get_error_message()
        # Return what we have
        return oBack


class Description(models.Model):
    """Description for a lemma"""

    toelichting = models.TextField("Omschrijving van het lemma", blank=True)
    bronnenlijst = models.TextField("Bronnenlijst bij het lemma", db_index=True, blank=True)
    boek = models.TextField("Boekaanduiding", db_index=True, null=True,blank=True)

    class Meta:
        #index_together = ['toelichting', 'bronnenlijst', 'boek']
        #index_together = ['toelichting', 'bronnenlijst']
        indexes = [
            models.Index(fields=['toelichting', 'bronnenlijst', 'boek'], name='descr_three'),
            models.Index(fields=['toelichting', 'bronnenlijst'], name='descr_two'),
            ]


    def __str__(self):
        return self.bronnenlijst

    def get_descr_sort(self):
        return self.toelichting

    def get_pk(self):
        """Check if this Description exists and return a PK"""
        qs = Description.objects.filter(bronnenlijst__iexact=self['bronnenlijst'], 
                                        boek__iexact=self['boek'],
                                        toelichting__iexact=self['toelichting'])
        if len(qs) == 0:
            iPk = -1
        else:
            iPk = qs[0].pk

        return iPk

    def get_item(self):
        """Return the identifier of the object described in self"""

        oErr = ErrHandle()
        try:
            # Get the parameters
            bronnenlijst = self['bronnenlijst']
            boek = self['boek']
            toelichting = ""
            if 'toelichting' in self:
                toelichting = self['toelichting']
            # Try find an existing item
            lstQ = []
            lstQ.append(Q(bronnenlijst__iexact=bronnenlijst))
            lstQ.append(Q(boek__iexact=boek))
            lstQ.append(Q(toelichting__iexact=toelichting))
            qItem = Description.objects.filter(*lstQ).first()
            # see if we get one value back
            if qItem == None:
                # add a new Description object
                descr = Description(bronnenlijst=bronnenlijst, boek=boek, toelichting=toelichting)
                descr.save()
                iPk = descr.pk
                qItem = descr
            else:
                # Get the pk of the first hit
                iPk = qItem.pk

            # Return the result
            return iPk, qItem
        except:
            oErr.DoError("Description/get_item error:")
            return -1, None

    def get_instance(options, instance, oTime = None):
        """Return the instance described by the options"""

        oErr = ErrHandle()
        bSpeedUp = False
        try:
            # Get the parameters
            bronnenlijst = options['bronnenlijst']
            boek = options['boek']
            toelichting = ""
            if 'toelichting' in options:
                toelichting = options['toelichting']
            # Check if we have an existing instance and if it equals that one
            if instance != None:
                if instance.bronnenlijst == bronnenlijst and instance.boek == boek and instance.toelichting == toelichting:
                    # Return this instance
                    return instance

            # SPEEDING UP:
            #  - If there was no previous instance, then just create a new one without searching any further.
            if bSpeedUp:
                qItem = None
            else:
                # Try find an existing item
                lstQ = []
                lstQ.append(Q(bronnenlijst__iexact=bronnenlijst))
                lstQ.append(Q(boek__iexact=boek))
                lstQ.append(Q(toelichting__iexact=toelichting))

                if oTime != None: iStart = get_now_time()
                qItem = Description.objects.filter(*lstQ).first()
                if oTime != None: oTime['search_Ds'] += get_now_time() - iStart

            # see if we get one value back
            if qItem == None:
                # add a new Description object
                if oTime != None: iStart = get_now_time()
                qItem = Description(bronnenlijst=bronnenlijst, boek=boek, toelichting=toelichting)
                qItem.save()
                if oTime != None: oTime['save'] += get_now_time() - iStart

            # Return the result
            return qItem
        except:
            oErr.DoError("Description/get_instance error:")
            return None


class Lemma(models.Model):
    """Lemma"""

    gloss = models.CharField("Gloss voor dit lemma", db_index=True, blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # toelichting = models.TextField("Omschrijving van het lemma", blank=True)
    # bronnenlijst = models.TextField("Bronnenlijst bij dit lemma", db_index=True, blank=True)
    # boek = models.TextField("Boekaanduiding", db_index=True, null=True,blank=True)
    lmdescr = models.ManyToManyField(Description, through='LemmaDescr')
    # A field that indicates this item may be showed
    toonbaar = models.BooleanField("Mag getoond worden", blank=False, default=True)

    class Meta:
        # Note: no index is possible, since lmdescr is many-to-many
        # index_together = ['gloss', 'lmdescr']
        verbose_name_plural = "Lemma's"

    def __str__(self):
        return self.gloss

    def get_pk(self):
        """Check if this lemma exists and return a PK"""
        qs = Lemma.objects.filter(gloss__iexact=self['gloss'])
        if len(qs) == 0:
            iPk = -1
        else:
            iPk = qs[0].pk

        return iPk

    def get_item(self):
        oErr = ErrHandle()
        try:
            # Get the parameters
            gloss = self['gloss']
            try:
                # OLD: lemma = Lemma.objects.get(gloss__iexact=gloss)
                lemma = Lemma.objects.get(gloss=gloss)
            except ObjectDoesNotExist:
                lemma = Lemma(gloss=gloss)
                lemma.save()
            # Get the pk of the lemma
            iPk = lemma.pk

            # Return the result
            return iPk
        except:
            oErr.DoError("Lemma/get_item error:")
            return -1

    def get_instance(options, oTime = None):
        """Return the instance described by the options"""

        oErr = ErrHandle()
        try:
            # Get the parameters
            gloss = options['gloss']
            # Make sure it is lower case
            gloss = gloss.lower()
            # Try find an existing item
            lstQ = []
            # lstQ.append(Q(gloss__iexact=gloss))
            lstQ.append(Q(gloss=gloss))

            if oTime != None: iStart = get_now_time()
            qItem = Lemma.objects.filter(*lstQ).first()
            if oTime != None: oTime['search_L'] += get_now_time() - iStart

            # see if we get one value back
            if qItem == None:
                if oTime != None: iStart = get_now_time()
                qItem = Lemma(gloss=gloss)
                qItem.save()
                if oTime != None: oTime['save'] += get_now_time() - iStart

            # Return the result
            return qItem
        except:
            oErr.DoError("Lemma/get_instance error:")
            return None

    def change_toonbaar():
        # Set all lemma's to 'toonbaar
        with transaction.atomic():
            for lemma in Lemma.objects.all():
                if lemma.toonbaar != True:
                    lemma.toonbaar = True
                    lemma.save()
        # Get a list of all lemma's that are NOT toonbaar
        lemma_show = Lemma.objects.filter(entry__aflevering__toonbaar=1).distinct()
        lemma_hide = Lemma.objects.exclude(Q(id__in=lemma_show))
        with transaction.atomic():
            for lemma in lemma_hide:
                lemma.toonbaar = False
                lemma.save()
        # Return positively
        return True


class LemmaDescr(models.Model):
    """Description belonging to a lemma"""

    lemma=models.ForeignKey(Lemma, on_delete=models.CASCADE)
    description=models.ForeignKey(Description, on_delete=models.CASCADE)

    class Meta:
        index_together = ['lemma', 'description']

    def get_item(self, oTime = None):
        oErr = ErrHandle()
        try:
            # Get the parameters
            lemma = self['lemma']
            description = self['description']
            # Try find an existing item
            lstQ = []
            lstQ.append(Q(lemma=lemma))
            lstQ.append(Q(description=description))

            if oTime != None: iStart = get_now_time()
            qItem = LemmaDescr.objects.filter(*lstQ).first()
            if oTime != None: oTime['search_LD'] += get_now_time() - iStart

            # see if we get one value back
            if qItem == None:
                # add a new Description object
                # lemdescr = LemmaDescr(lemma=Lemma.objects.get(id=lemma), description=Description.objects.get(id=description))
                if oTime != None: iStart = get_now_time()
                qItem = LemmaDescr(lemma=lemma, description=description)
                qItem.save()
                if oTime != None: oTime['save'] += get_now_time() - iStart
            # Get the pk of the first hit
            iPk = qItem.pk

            # Return the result
            return iPk
        except:
            oErr.DoError("LemmaDescr/get_item error:")
            return -1

    def get_instance(options):
        """Return the instance described by the options"""

        oErr = ErrHandle()
        try:
            # Get the parameters, which are *instances* (not id's)
            lemma = options['lemma']
            description = options['description']
            # Try find an existing item
            lstQ = []
            lstQ.append(Q(lemma=lemma))
            lstQ.append(Q(description=description))

            if oTime != None: iStart = get_now_time()
            qItem = LemmaDescr.objects.filter(*lstQ).first()
            if oTime != None: oTime['search_LD'] += get_now_time() - iStart

            # see if we get one value back
            if qItem == None:
                # add a new Description object
                if oTime != None: iStart = get_now_time()
                qItem = LemmaDescr(lemma=lemma, description=description)
                qItem.save()
                if oTime != None: oTime['save'] += get_now_time() - iStart

            # Return the result
            return qItem
        except:
            oErr.DoError("LemmaDescr/get_instance error:")
            return None
    

class Coordinate(models.Model):
    """Kloeke code and real-life coordinates"""

    # [1] The actual (new) KloekeCode
    kloeke = models.CharField("Plaatscode (Kloeke)", blank=False, max_length=6, default="xxxxxx")
    # [0-1] The place name
    place = models.CharField("Place name", db_index=True, blank=True, max_length=MAX_LEMMA_LEN)
    # [0-1] The province
    province = models.CharField("Province", db_index=True, blank=True, max_length=MAX_LEMMA_LEN)
    # [0-1] The country name
    country = models.CharField("Country", db_index=True, blank=True, max_length=MAX_LEMMA_LEN)
    # [0-1] The dictionary in which this occurs
    dictionary = models.CharField("Dictionary", db_index=True, blank=True, max_length=MAX_LEMMA_LEN)
    # [0-1] The point coordinates
    point = models.CharField("Coordinates", db_index=True, blank=True, max_length=MAX_LEMMA_LEN)

    def __str__(self):
        sBack = "{}: {}".format(self.kloeke, self.place)
        return sBack


class Dialect(models.Model):
    """Dialect"""

    # [1] The location name (city)
    stad = models.CharField("Dialectlocatie", db_index=True, blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # [1] The 'old' Kloeke code
    code = models.CharField("Plaatscode (Kloeke)", blank=False, max_length=6, default="xxxxxx")
    # [1] The 'new' Kloeke code
    nieuw = models.CharField("Plaatscode (Nieuwe Kloeke)", db_index=True, blank=False, max_length=6, default="xxxxxx")
    # [1] The area
    streek = models.CharField("Streek", db_index=True, blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")

    # A field that indicates this item may be showed
    toonbaar = models.BooleanField("Mag getoond worden", blank=False, default=True)
    # Note: removed 'dialect_toelichting' in accordance with issue #22 of WLD
    # toelichting = models.TextField("Toelichting bij dialect", blank=True)

    # [0-1] Would like to have a coordinate for this dialect
    coordinate = models.ForeignKey(Coordinate, null=True, blank=True, on_delete=models.SET_NULL, related_name="coordinatedialects")

    # [1] Calculated field: number of 'Entry' elements for this dialect
    count = models.IntegerField("Number of entries", default=0)

    class Meta:
        verbose_name_plural = "Dialecten"
        index_together = ['stad', 'code', 'nieuw']

    def __str__(self):
        return self.nieuw

    def get_pk(self):
        """Check if this dialect exists and return a PK"""
        qs = Dialect.objects.filter(stad__iexact=self['stad'], 
                                  nieuw__iexact=self['nieuw']).first()
        if len(qs) == 0:
            iPk = -1
        else:
            iPk = qs[0].pk

        return iPk

    def get_item(self, oTime = None):
        oErr = ErrHandle()
        try:
            # Get the parameters
            stad = self['stad']
            nieuw = self['nieuw']
            # Try find an existing item
            lstQ = []
            lstQ.append(Q(stad__iexact=stad))
            lstQ.append(Q(nieuw__iexact=nieuw))

            if oTime != None: iStart = get_now_time()
            qItem = Dialect.objects.filter(*lstQ).first()
            if oTime != None: oTime['search_Dt'] += get_now_time() - iStart

            # see if we get one value back
            if qItem == None:
                # add a new Dialect object
                if oTime != None: iStart = get_now_time()
                qItem = Dialect(stad=stad, nieuw=nieuw, code='-')
                qItem.save()
                if oTime != None: oTime['save'] += get_now_time() - iStart
            # Get the pk of the first hit
            iPk = qItem.pk

            # Return the result
            return iPk
        except:
            oErr.DoError("Dialect/get_item error:")
            return -1

    def change_toonbaar():
        # Set all inst's to 'toonbaar
        with transaction.atomic():
            for inst in Dialect.objects.all():
                if inst.toonbaar != True:
                    inst.toonbaar = True
                    inst.save()
        # Get a list of all inst's that are NOT toonbaar
        dialect_show = Dialect.objects.filter(entry__aflevering__toonbaar=1).distinct()
        dialect_hide = Dialect.objects.exclude(Q(id__in=dialect_show))
        with transaction.atomic():
            for inst in dialect_hide:
                inst.toonbaar = False
                inst.save()
        # Return positively
        return True


class Trefwoord(models.Model):
    """Trefwoord"""

    woord = models.CharField("Trefwoord", db_index=True, blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    toelichting = models.TextField("Toelichting bij trefwoord", blank=True)
    # A field that indicates this item may be showed
    toonbaar = models.BooleanField("Mag getoond worden", blank=False, default=True)

    class Meta:
        verbose_name_plural = "Trefwoorden"
        index_together = ['woord', 'toelichting']

    def __str__(self):
        return self.woord

    def get_pk(self):
        """Check if this dialect exists and return a PK"""
        qs = Trefwoord.objects.filter(woord__iexact=self['woord'])
        if 'toelichting' in self: 
            qs = qs.filter(toelichting__iexact=self['toelichting'])
        if len(qs) == 0:
            iPk = -1
        else:
            iPk = qs[0].pk

        return iPk

    def get_item(self, oTime = None):
        oErr = ErrHandle()
        try:
            toelichting = None
            # Get the parameters
            woord = self['woord']
            # Make sure it is lower case
            woord = woord.lower()
            # Try find an existing item
            lstQ = []
            # lstQ.append(Q(woord__iexact=woord))
            lstQ.append(Q(woord=woord))
            if 'toelichting' in self:
                toelichting = self['toelichting']
                lstQ.append(Q(toelichting__iexact = toelichting))

            if oTime != None: iStart = get_now_time()
            qItem = Trefwoord.objects.filter(*lstQ).first()
            if oTime != None: oTime['search_T'] += get_now_time() - iStart

            # see if we get one value back
            if qItem == None:
                # add a new Dialect object
                if oTime != None: iStart = get_now_time()
                qItem = Trefwoord(woord=woord)
                if toelichting != None:
                    qItem.toelichting = toelichting
                qItem.save()
                if oTime != None: oTime['save'] += get_now_time() - iStart
            # Get the pk of the first hit
            iPk = qItem.pk

            # Return the result
            return iPk
        except:
            oErr.DoError("Trefwoord/get_item error:")
            return -1

    def change_toonbaar():
        # Set all inst's to 'toonbaar
        with transaction.atomic():
            for inst in Trefwoord.objects.all():
                if inst.toonbaar != True:
                    inst.toonbaar = True
                    inst.save()
        # Get a list of all inst's that are NOT toonbaar
        trefwoord_show = Trefwoord.objects.filter(entry__aflevering__toonbaar=1).distinct()
        trefwoord_hide = Trefwoord.objects.exclude(Q(id__in=trefwoord_show))
        with transaction.atomic():
            for inst in trefwoord_hide:
                inst.toonbaar = False
                inst.save()
        # Return positively
        return True


class Deel(models.Model):
    """Deel van de woordenboekencollectie"""

    class Meta:
        verbose_name_plural = "Delen"

    # Titel van dit deel
    titel = models.CharField("Volledige titel", blank=False, max_length=MAX_TITEL_LEN, default="(unknown)")
    # Nummer van dit deel
    nummer = models.IntegerField("Nummer", blank=False, default=0)
    # Allow for comments for this 'deel'
    toelichting = models.TextField("Toelichting bij dit deel", blank=True)

    class Meta:
        index_together = ['titel', 'nummer', 'toelichting']

    def __str__(self):
        return self.titel

    def romeins(self):
        return int_to_roman(self.nummer)
    

class Info(models.Model):
    """Informatiebestand (csv)"""

    # Nummer van het deel (I, II, III)
    deel = models.IntegerField("Deel", blank=False, default=0)
    # Nummer van de sectie (indien van toepassing -- subcategorie voor deel 3)
    sectie = models.IntegerField("Sectie (optioneel)", blank=True, null=True)
    # Nummer van de aflevering
    aflnum = models.IntegerField("Aflevering", blank=False, default=0)
    # Whether/when processed
    processed = models.CharField("Verwerkt", blank=True, max_length=MAX_LEMMA_LEN)
    # Number of read and skipped lines
    read = models.IntegerField("Gelezen", blank=False, default=0)
    skipped = models.IntegerField("Overgeslagen", blank=False, default=0)
    # Het bestand dat ge-upload wordt
    csv_file = models.FileField(upload_to="csv_files/")

    def reset_item(self):
        # Reset the 'Processed' comment
        self.processed = ""
        # Reset the amount of items read and skipped
        self.read = 0
        self.skipped = 0
        # Save changes
        self.save()

    def clear_item(self):
        # Reset the 'Processed' comment
        self.processed = ""
        # Reset the amount of items read and skipped
        self.read = 0
        self.skipped = 0
        # Remove the CSV-file from where it is stored
        csv_file = self.csv_file.path
        os.remove(csv_file)
        # Reset the CSV-file
        self.csv_file = ""
        # Save changes
        self.save()


class Status(models.Model):
    """Status of importing a CSV file """

    # Number of read and skipped lines
    read = models.IntegerField("Gelezen", blank=False, default=0)
    skipped = models.IntegerField("Overgeslagen", blank=False, default=0)
    status = models.TextField("Status", blank=False, default="idle")
    method = models.CharField("Reading method", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # Link to the Info
    info = models.ForeignKey(Info, blank=False, on_delete=models.CASCADE, related_name="info_statuses")

    def set_status(self, sStatus, sMsg = None):
        self.status = sStatus
        self.save()


class Repair(models.Model):
    """Definition and status of a repair action"""

    # Definition of this repair type
    repairtype = models.CharField("Soort reparatie", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # Status of this repair action
    status = models.TextField("Status", blank=False, default="idle")

    def set_status(self, sStatus):
        self.status = sStatus
        self.save()


class Aflevering(models.Model):
    """Aflevering van een woordenboek"""

    # The 'naam' is the full name of the PDF (without path) in which information is stored
    naam = models.CharField("PDF naam", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # The 'deel' is the main category of the books
    deel = models.ForeignKey(Deel, db_index=True, blank=False, on_delete=models.CASCADE, related_name="deel_afleveringen")
    # The 'sectie' is a sub-category used for instance in deel 3
    sectie = models.IntegerField("Sectie (optioneel)", db_index=True, blank=True, null=True)
    # The 'aflnum' is the actual number of the aflevering 
    aflnum = models.IntegerField("Aflevering", db_index=True, blank=False, default=0)
    # A field that indicates this item also has an Inleiding
    inleiding = models.BooleanField("Heeft inleiding", blank=False, default=False)
    # A field that indicates this item may be showed
    toonbaar = models.BooleanField("Mag getoond worden", blank=False, default=True)
    # The year of publication of the book
    jaar = models.IntegerField("Jaar van publicatie", blank=False, default=1900)
    # The authors for this book
    auteurs = models.CharField("Auteurs", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # The title of this aflevering
    afltitel = models.CharField("Boektitel", blank=False, max_length=MAX_TITEL_LEN, default="(unknown)")
    # The title of this sectie
    sectietitel = models.CharField("Sectietitel", blank=True, max_length=MAX_TITEL_LEN, default="")
    # The place(s) of publication
    plaats = models.CharField("Plaats van publicatie", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # Any additional information
    toelichting = models.TextField("Toelichting bij aflevering", blank=True)

    class Meta:
        verbose_name_plural = "Afleveringen"
        index_together = ['deel', 'sectie', 'aflnum']

    def __str__(self):
        return self.naam

    def save(self, force_insert = False, force_update = False, using = None, update_fields = None):
        # Initialisations
        bToonbaarChanged = False
        # See if toonbaar has changed
        if self.pk != None:
            orig = Aflevering.objects.get(pk=self.pk)
            bToonbaarChanged = (self.toonbaar != orig.toonbaar)
        
        # Perform the normal save action
        result = super(Aflevering, self).save(force_insert, force_update, using, update_fields)

        # Action if Toonbaar has changed
        if bToonbaarChanged:
            # Adapt Lemma, Trefwoord and Dialect instances
            Lemma.change_toonbaar()
            Trefwoord.change_toonbaar()
            Dialect.change_toonbaar()
        return result

    def get_number(self):
        if self.sectie == None:
            iNumber = self.aflnum
        else:
            iNumber = self.sectie * 10 + self.aflnum
        return iNumber

    def get_summary(self):
        sSum = int_to_roman(self.deel.nummer) + "-"
        if self.sectie != None:
            sSum += str(self.sectie) + "-"
        sSum += str(self.aflnum)
        return sSum

    def get_pdf(self):
        # Construct the name of the file itself
        sPdf =  "wgd-{}/{}".format(self.deel.nummer,self.naam)
        # See where it should be
        sFile = os.path.abspath(os.path.join(STATIC_ROOT, "dictionary/content/pdf", sPdf))
        # Check if it is there
        if not os.path.exists(sFile):
            ErrHandle.Status(None, "get_pdf cannot find: {}".format(sFile))
            # It doesn't exists, so return NONE
            sPdf = ""
        return sPdf

    def get_pk(self):
        """Check if this aflevering exists and return a PK"""
        qs = Aflevering.objects.filter(deel__nummer__iexact=self['deel'], 
                                  aflnum__iexact = self['aflnum'])
        if self['sectie'] != None:
            qs = qs.filter(sectie__iexact = self['sectie'])

        if len(qs) == 0:
            iPk = -1
        else:
            iPk = qs[0].pk

        return iPk

    def get_item(self):
        oErr = ErrHandle()
        try:
            # Get the parameters
            deel = self['deel']
            sectie = self['sectie']
            aflnum = self['aflnum']
            # Try find an existing item
            lstQ = []
            lstQ.append(Q(deel__nummer__iexact=deel))
            lstQ.append(Q(aflnum__iexact=aflnum))
            if sectie != None:
                lstQ.append(Q(sectie__iexact = sectie))
            qItem = Aflevering.objects.filter(*lstQ).first()
            # see if we get one value back
            if qItem == None:
                # We cannot add a new item
                iPk = -1
            else:
                # Get the pk of the first hit
                iPk = qItem.pk

            # Return the result
            return iPk
        except:
            oErr.DoError("Aflevering/get_item error:")
            return -1


class Mijn(models.Model):
    """De mijn waar de sprekers werken"""

    class Meta:
        verbose_name_plural = "Mijnen"

    naam = models.CharField("Mijn", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    locatie = models.CharField("Locatie", blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    toelichting = models.TextField("Toelichting bij mijn", blank=True)

    def __str__(self):
        return self.naam

    def get_pk(self):
        """Check if this [mijn] exists and return a PK"""
        qs = Mijn.objects.filter(naam__iexact=self['naam'])
        if len(qs) == 0:
            iPk = -1
        else:
            iPk = qs[0].pk

        return iPk

    def get_item(self, oTime = None):
        oErr = ErrHandle()
        try:
            # Get the parameters
            naam = self['naam']
            # Try find an existing item
            lstQ = []
            lstQ.append(Q(naam__iexact=naam))

            if oTime != None: iStart = get_now_time()
            qItem = Mijn.objects.filter(*lstQ).first()
            if oTime != None: oTime['search_M'] += get_now_time() - iStart

            # see if we get one value back
            if qItem == None:
                # add a new Dialect object
                if oTime != None: iStart = get_now_time()
                qItem = Mijn(naam=naam)
                qItem.save()
                if oTime != None: oTime['save'] += get_now_time() - iStart
            # Get the pk of the first hit
            iPk = qItem.pk

            # Return the result
            return iPk
        except:
            oErr.DoError("Mijn/get_item error:")
            return -1


class Entry(models.Model):
    """Dictionary entry"""

    class Meta:
        verbose_name_plural = "Entries"
        ordering = ['lemma', 'woord']
        permissions = ( ('search_gloss', 'Can search/view/edit full entry details'),
                       )
        index_together = [
            ["dialect", "lemma", "trefwoord", "woord"],
            ["lemma", "aflevering"],
          ]

    def __str__(self):
        return self.woord + '_' + self.dialect.nieuw

    # Lemma: obligatory
    lemma = models.ForeignKey(Lemma, db_index=True, blank=False, on_delete=models.CASCADE) #, related_name="lemma_entries")
    # Description: this description should be one and the same for a whole lemma, but this is not true in practice
    descr = models.ForeignKey(Description, db_index=True, blank=False, on_delete=models.CASCADE, related_name="descr_entries")
    # Dialect: obligatory
    dialect = models.ForeignKey(Dialect, db_index=True, blank=False, on_delete=models.CASCADE, related_name="dialect_entries")
    # Trefwoord: obligatory
    trefwoord = models.ForeignKey(Trefwoord, db_index=True, blank=False, on_delete=models.CASCADE, related_name="trefwoord_entries")
    # Mijn [0-1]
    # mijn = models.ForeignKey(Mijn, blank = True, null=True)
    # Mijn [0-n]
    mijnlijst = models.ManyToManyField(Mijn, db_index=True, through='EntryMijn')
    # Aflevering [1]
    aflevering = models.ForeignKey(Aflevering, db_index=True, blank=False, on_delete=models.CASCADE, related_name="aflevering_entries")
    # Dialectal entry: obligatory
    woord = models.CharField("Dialectopgave", db_index=True, blank=False, max_length=MAX_LEMMA_LEN, default="(unknown)")
    # Notes to this entry: optional
    toelichting = models.TextField("Toelichting", db_index=True, blank=True)
    # See WLD issue #22
    kloeketoelichting = models.TextField("Toelichting bij dialectopgave voor een bepaalde kloekelocatie", blank=True)

    # ============ FIELDS SPECIFICALLY FOR WGD ================================
    # [0-1] Optional subvraagletter
    subvraag = models.CharField("Subvraagletter", blank=True, max_length=MAX_LEMMA_LEN)
    # [1] Entry appears in the published book or not
    inwoordenboek = models.CharField("In gepubliceerd woordenboek", choices=build_abbr_list(ENTRY_INDICT), 
                        db_index = True, max_length=5, help_text=get_help(ENTRY_INDICT), default="true")
    # [0-1] Optional remark of student assistant
    opmerking = models.TextField("Opmerking student-assistent(e)", blank=True)
    # =========================================================================

    def get_trefwoord_woord(self):
        return self.trefwoord.woord + '_' + self.woord

    def get_trefwoord_lemma_woord(self):
        return self.trefwoord.woord + '_' +self.lemma.gloss + "_" + self.woord

    def dialectopgave(self):
        sWoord = "*"
        # Are we allowed to show it?
        if self.aflevering.toonbaar:
            sWoord = self.woord
        return sWoord

    def get_toelichting(self):
        return self.toelichting

    def get_aflevering(self):
        afl = self.aflevering
        sAfl = "d" + str(afl.deel.nummer) + "-"
        if afl.sectie != None:
            sAfl += "s" + str(afl.sectie) + "-"
        sAfl += "a" + str(afl.aflnum)
        return sAfl

    def get_lemma_gloss(self):
        return self.lemma.gloss + '_' + self.woord

    def get_row(self):
        arRow = []
        arRow.append(self.lemma.gloss)
        arRow.append(self.trefwoord.woord)
        arRow.append(self.woord)
        arRow.append(self.dialect.nieuw)
        arRow.append(self.aflevering.naam)
        arRow.append(self.descr.bronnenlijst)
        return arRow

    def get_tsv(self):
        return self.lemma.gloss + '\t' + self.trefwoord.woord + '\t' + self.woord + '\t' + self.dialect.nieuw + '\t' + self.aflevering.naam

    def get_pk(self):
        """Check if this [entry] exists and return a PK"""
        qs = Entry.objects.filter(woord__iexact=self['woord'], 
                                  toelichting__iexact=self['toelichting'],
                                  kloeketoelichting__iexact=self['kloeketoelichting'],
                                  lemma__pk=self['lemma'],
                                  dialect__pk = self['dialect'],
                                  trefwoord__pk = self['trefwoord'],
                                  aflevering__pk = self['aflevering'])
        if 'mijn' in self:
            qs = qs.filter(mijn__pk = self['naam'])

        if len(qs) == 0:
            iPk = -1
        else:
            iPk = qs[0].pk

        return iPk

    def get_item(self):
        mijnPk = None
        kloeketoelichting=""

        # Get the parameters out of [self]
        woord = self['woord']
        toelichting = self['toelichting']
        lemmaPk = self['lemma']
        dialectPk = self['dialect']
        trefwoordPk = self['trefwoord']
        afleveringPk = self['aflevering']
        if 'kloeketoelichting' in self:
            kloeketoelichting = self['kloeketoelichting']
        if 'mijn' in self:
            mijnPk = self['mijn']

        # Try find an existing item
        lstQ = []
        lstQ.append(Q(woord__iexact=woord))
        lstQ.append(Q(toelichting__iexact=toelichting))
        lstQ.append(Q(lemma__pk=lemmaPk))
        lstQ.append(Q(dialect__pk = dialectPk))
        lstQ.append(Q(trefwoord__pk = trefwoordPk))
        lstQ.append(Q(aflevering__pk = afleveringPk))
        lstQ.append(Q(mijn__pk = mijnPk))
        lstQ.append(Q(kloeketoelichting = kloeketoelichting))

        qs = Entry.objects.filter(*lstQ)
        # see if we get one unique value back
        iLen = len(qs)
        if iLen == 0:
            # Get the objects from the pk's
            lemma      = Lemma.objects.get(pk=lemmaPk)
            dialect    = Dialect.objects.get(pk=dialectPk)
            trefwoord  = Trefwoord.objects.get(pk=trefwoordPk)
            aflevering = Aflevering.objects.get(pk=afleveringPk)
            if mijnPk != None:
                mijn = Mijn.objects.get(pk=mijnPk)
                # add a new Dialect object
                entry = Entry(woord=woord, toelichting = toelichting, lemma=lemma,
                              dialect = dialect, trefwoord = trefwoord,
                              kloeketoelichting = kloeketoelichting,
                              aflevering = aflevering, mijn = mijn)
            else:
                # add a new Dialect object
                entry = Entry(woord=woord, toelichting = toelichting, lemma=lemma,
                              dialect = dialect, trefwoord = trefwoord,
                              kloeketoelichting = kloeketoelichting,
                              aflevering = aflevering)
            entry.save()
            iPk = entry.pk
        else:
            # Get the pk of the first hit
            iPk = qs[0].pk

        # Return the result
        return iPk


class EntryMijn(models.Model):
    """Connection between Entry and Mijn"""

    entry=models.ForeignKey(Entry, db_index=True, on_delete=models.CASCADE)
    mijn=models.ForeignKey(Mijn, db_index=True, on_delete=models.CASCADE)

    def get_item(self, bSet):
        # Get the parameters
        entry = self['entry']
        mijn = self['mijn']
        # Try find an existing item
        qItem = EntryMijn.objects.filter(entry=entry, 
                                         mijn=mijn).first()
        # see if we get one value back
        if qItem == None:
            # add a new Description object
            if bSet:
                # Just add this link; do not start looking for Entry or Mijn
                entrymijn = EntryMijn(entry_id=entry, mijn_id=mijn)
            else:
                entrymijn = EntryMijn(entry=Entry.objects.get(id=entry), mijn=Mijn.objects.get(id=mijn))
            entrymijn.save()
            iPk = entrymijn.pk
        else:
            # Get the pk of the first hit
            iPk = qItem.pk

        # Return the result
        return iPk


# ============================= Fixture Database Classes ===========================
class FixSkip:
    """Fixture skips"""

    bFirst = True
    fl_out = None

    def __init__(self, output_file):
        # Clear the output file, replacing it with a list starter
        self.fl_out = io.open(output_file, "w", encoding='utf-8')
        self.fl_out.write("")
        self.fl_out.close()
        # Make sure we keep the output file name
        self.output_file = output_file
        # Open the file for appending
        self.fl_out = io.open(output_file, "a", encoding='utf-8')

    def append(self, sLine):
        # Add a newline
        sLine += "\n"
        # Add the object         
        self.fl_out.writelines(sLine)

    def close(self):
        # Close the output file
        self.fl_out.close()


class FixOut:
    """Fixture output"""

    bFirst = True      # Indicates that the first output string has been written
    fl_out = None      # Output file

    def __init__(self, output_file):
        # Clear the output file, replacing it with a list starter
        self.fl_out = io.open(output_file, "w", encoding='utf-8')
        self.fl_out.write("[")
        self.fl_out.close()
        # Make sure we keep the output file name
        self.output_file = output_file
        # Open the file for appending
        self.fl_out = io.open(output_file, "a", encoding='utf-8')

    def append(self, sModel, iPk, **oFields):
        # Possibly add comma
        self.do_comma()
        # Create entry object
        oEntry = {"model": sModel, 
                  "pk": iPk, "fields": oFields}
        # Add the object         
        self.fl_out.writelines(json.dumps(oEntry, indent=2))

    def do_comma(self):
        # Is this the first output?
        if self.bFirst:
            self.bFirst = False
        else:
            self.fl_out.writelines(",")

    def close(self):
        # Append the final [
        self.fl_out.writelines("]")
        # Close the output file
        self.fl_out.close()

    def findItem(self, arItem, **oFields):
        try:
            # Sanity check
            if len(arItem) == 0:
                return -1
            # Make sure numeric values are 
            # Check all the items given: do it reversed, because then we have the best chance of getting something
            for it in reversed(arItem):
                # Assume we are okay
                bFound = True
                # Look through all the (k,v) pairs of [oFields]
                for (k,v) in oFields.items():
                    try:
                        if k in oFields and getattr(it, k) != v:
                            bFound = False
                            break
                    except:
                        # No need to stop here
                        a = 1
                if bFound:
                    return getattr(it, 'pk')
    
            # getting here means we haven't found it
            return -1
        except:
            errHandle.DoError("FixOut/findItem", True)



    def get_pk(self, oCls, sModel, bSearch, **oFields):
        try:
            iPkItem = -1
            # Look for this item in the list that we have
            if bSearch:
                iPkItem = self.findItem(oCls.lstItem, **oFields)
            if iPkItem < 0:
                # it is not in the list: add it
                if 'pk' in oFields:
                    # Get the pk value and *remove* the key from the field
                    iPkItem = oFields.pop('pk')                    
                else:
                    iPkItem = len(oCls.lstItem)

                iPkItem += 1
                newItem = fElement(iPkItem, **oFields)
                oCls.lstItem.append(newItem)
                # Add the item to the output
                self.append(sModel, iPkItem, **oFields)

            # Return the pK
            return iPkItem
        except:
            errHandle.DoError("FixOut/get_pk", True)
    

class fElement:

    def __init__(self, iPk, **kwargs):
        for (k,v) in kwargs.items():
            setattr(self, k, v)
        self.pk = iPk


class fLemma:
    """Lemma information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known lemma's

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, gloss=item.gloss))
                self.pk = item.pk


class fDescr:
    """Description information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known lemma's

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, 
                                             bronnenlijst=item.bronnenlijst, 
                                             toelichting=item.toelichting, 
                                             boek=item.boek))
                self.pk = item.pk


class fLemmaDescr:
    """Connection between lemma and description information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known lemma's

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, lemma=item.lemma, description=item.description))
                self.pk = item.pk


class fEntryMijn:
    """Connection between entry and mijn information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known items

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, entry=item.entry, mijn=item.mijn))
                self.pk = item.pk


class fDialect:
    """Dialect information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known dialects

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                added = fElement(item.pk, stad=item.stad, nieuw=item.nieuw)
                self.lstItem.append(added)
                self.pk = item.pk


class fTrefwoord:
    """Trefwoord information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known items

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, woord=item.woord))
                self.pk = item.pk


class fMijn:
    """Mijn information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known items

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, naam=item.naam))
                self.pk = item.pk


class fAflevering:
    """Aflevering information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known dialects

    def load(self, qs):
        try:
            if qs:
                for item in qs:
                    # Add this item to the list we have
                    if item.sectie != None:
                        try:
                            added = fElement(item.pk, deel=item.deel, sectie=item.sectie,aflnum=item.aflnum)
                        except:
                            a = 1
                    else:
                        try:
                            added = fElement(item.pk, deel=item.deel, aflnum=item.aflnum)
                        except:
                            a = 1
                    self.lstItem.append(added)
                    self.pk = item.pk
        except:
            errHandle.DoError("fAflevering", True)


class fEntry:
    """Entry information to fixture"""

    pk = 0         # Initialise PK
    lstItem = []   # Array of known dialects

    def load(self, qs):
        if qs:
            for item in qs:
                # Add this item to the list we have
                self.lstItem.append(fElement(item.pk, woord=item.woord, 
                                      toelichting=item.toelichting, 
                                      kloeketoelichting=item.kloeketoelichting, 
                                      lemma=item.lemma, 
                                      dialect=item.dialect, 
                                      trefwoord=item.trefwoord, 
                                      aflevering=item.aflevering))
                self.pk = item.pk


class Processor():
    """How to process an Excel (or CSV) file that contains entries"""

    frow = 2                # First row to be processed
    offset = 0              # Column number offset
    row = 0                 # Current row
    cols = 10               # Number of columns to be read
    oErr = ErrHandle()      # Error handling
    ws = None               # The worksheet
    oRow = None             # The cells of one row
    oCol = {}               # Mapping of column name to number
    type = "excel"          # The type of object we have: 'excel', 'csv_a', 'csv_b'
    col_lemma = -1          # Lemmatitel
    col_vraagn = -1         # vraagnummer
    col_vraagt = -1         # tekst van de vraag
    col_bron = -1           # bron
    col_kloeke = -1         # kloeke-code
    col_stand = -1          # standaardspelling
    col_dialw = -1          # dialectwoord
    col_indict = -1         # in woordenboek
    col_opmst = -1          # opmerking studentassistent / Inge
    col_opm = -1            # opmerkingen
    col_subvr = -1          # subvraagletter

    def __init__(self, sFile):
        # Open the workbook
        wb = openpyxl.load_workbook(sFile, read_only=True)
        # Access the default worksheet
        self.ws = wb.get_active_sheet()
        # Start an iterator for the rows
        self.oRows = iter(self.ws)
        self.row = 1
        # Skip rows until we are at the point where the first row starts
        while self.row < self.frow:
            oRow = next(self.oRows)
            if self.row == 1:
                # This is the top row that contains the column names
                self.process_col_names(oRow)
            self.row += 1

    def process_col_names(self, oRow):
        """Map the column names to the column numbers
        
        This method makes sure that self.oCol has at least these fields:
            recordid, vraagnummer, vraagtekst, dialectwoord,
            standaardspelling, lemmatitel, kloeke-code, bron, opmerkingen,
            lijstnummer, woordenboek, studass
        Optional fields are:
            subvraagletter
            nederlands
        """

        try:
            lNames = [cell.value for cell in oRow]

            for idx, col_name in enumerate(lNames):
                # Sanity check
                if col_name != None:
                    # Make sure we are working with lower case
                    col_name = col_name.lower()
                    if "tekst v.d." in col_name or "tekst van de" in col_name:
                        self.oCol["vraagtekst"] = idx
                    elif "woordenboek" in col_name:
                        self.oCol["inwoordenboek"] = idx
                    elif " inge" in col_name or "studass" in col_name:
                        self.oCol["studass"] = idx
                    elif "nederlands" in col_name:
                        self.oCol["nederlands"] = idx
                    else:
                        self.oCol[col_name] = idx
            # Now extract the needed elements from oCol
            self.col_lemma = self.oCol['lemmatitel']
            self.col_vraagn = self.oCol['vraagnummer']
            self.col_vraagt = self.oCol['vraagtekst']
            self.col_bron = self.oCol['bron']
            self.col_kloeke = self.oCol['kloeke-code']
            self.col_stand = self.oCol['standaardspelling']
            self.col_dialw = self.oCol['dialectwoord']
            self.col_indict = self.oCol['inwoordenboek']
            self.col_opm = self.oCol['opmerkingen']
            if 'studass' in self.oCol:
                self.col_opmst = self.oCol['studass']
            if 'subvraagletter' in self.oCol:
                self.col_subvr = self.oCol['subvraagletter']
        except:
            msg = self.oErr.get_error_message()
            self.oErr.DoError("Processor.process_col_names() error")

    def partToLine(self):
        """Convert the contents of the current self.oRow into an object"""
        oBack = {}
        # User should supply its own code; this is just a starter
        return oBack

    def next_row(self):
        try:
            if self.type == "excel":
                # Get the next row in an Excel file
                self.oRow = next(self.oRows, None)
            elif self.type.startswith("csv"):
                # Go to the next row of a CSV file
                pass
            # Make sure the row counter is adapted
            self.row += 1
            # Return the object of this row
            return self.oRow
        except:
            msg = self.oErr.get_error_message()
            self.oErr.DoError("Processor.next_row() error")

            return None

    def is_valid(self):
        """Check if current row is valid"""
        return True

    def line(self):
        """Return a string representation of myself"""

        sBack = ""
        try:
            if self.type == "excel":
                # Put the values into an array
                lCells = [cell.value for cell in self.oRow]
                for idx, value in enumerate(lCells):
                    if value == None:
                        lCells[idx] = ""
                    else:
                        lCells[idx] = str(lCells[idx])
                sBack = "\t".join(lCells)
            else:
                # TODO: define how this works for a CSV
                pass
        except:
            msg = self.oErr.get_error_message()
            self.oErr.DoError("Processor.line() error")

        return sBack


class WgdProcessor(Processor):
    """Specify how WGD input should be processed
    
    This class relies on column names having been correctly identified \
    by the process_col_names() method of Processor.
    """

    def partToLine(self):
        """Convert the contents of the current self.oRow into an object"""

        oBack = {}
        try:
            # Put the values into an array
            oCells = [cell.value for cell in self.oRow]
            # Double check: is this row valid?
            if oCells[0] != None and oCells[0] != "":
                offset = self.offset
                # The row is valid: create the object
                oBack['lemma_name'] = oCells[self.col_lemma]        # (lemmatitel)
                oBack['lemma_bronnenlijst'] = ""                    # Not applicable
                oBack['lemma_toelichting'] = "{}: {}".format(       
                    oCells[self.col_vraagn],                        # (vraagnummer) +
                    oCells[self.col_vraagt])                        # (tekst van de vraag)
                oBack['lemma_boek'] = ""                            # Not applicable
                oBack['dialect_stad'] = oCells[self.col_bron]       # (called 'bron')
                oBack['dialect_nieuw'] = oCells[self.col_kloeke]    # (kloeke-code)
                oBack['dialect_kloeke'] = ""                        # empty
                oBack['trefwoord_name'] = oCells[self.col_stand]    # (standaardspelling)
                oBack['trefwoord_toelichting'] = ""                 # empty
                oBack['dialectopgave_name'] = oCells[self.col_dialw]        # (dialectwoord)
                oBack['dialectopgave_toelichting'] = oCells[self.col_opm]   # (opmerkingen)
                oBack['dialectopgave_kloeketoelichting'] = ""       # empty
                # UNUSED: field 8 - lijstnummer

                # Fields specific to WGD
                oBack['inwoordenboek'] = oCells[self.col_indict]    # (In woordenboek j/n)
                oBack['opmerking'] = ""
                oBack['subvraag'] = ""
                if self.col_opmst > 0:
                    oBack['opmerking'] = oCells[self.col_opmst]     # (Opmerkingen studass)
                if self.col_subvr > 0:
                    oBack['subvraag'] = oCells[self.col_subvr]      # (subvraagletter; empty for VELUWE)

                # Make sure NONE gets replaced by ""
                for k,v in oBack.items():
                    if v == None:
                        oBack[k] = ""
                    else:
                        # make sure we only have STRING variables
                        oBack[k] = str(v)

                # Some additional adaptations
                oBack['dialect_nieuw'] = oBack['dialect_nieuw'].replace(" ", "")
            # Return what was found
            return oBack
        except:
            msg = errHandle.get_error_message()
            self.oErr.DoError("read_row error")
            return None

    def is_valid(self):
        try:
            if self.row < self.frow: return False
            if self.oRow == None: return False
            cell = self.oRow[0]
            bValid = (cell.value != None and cell.value != "")
            return bValid
        except:
            msg = self.oErr.get_error_message()
            self.oErr.DoError("Processor.line() error")
            return False


   
# ----------------------------------------------------------------------------------
# Name :    excel_to_fixture
# Goal :    Convert XML file into a fixtures file
# History:
#  10/oct/2018   ERK Created
# ----------------------------------------------------------------------------------
def excel_to_fixture(xlsx_file, iDeel, iSectie, iAflevering, iStatus, bUseDbase=False, bUseOld=False):
    """Process an EXCEL file with entry definitions"""

    oBack = {}          # What we return
    oStatus = None
    sVersie = ""        # The version we are using--this depends on the column names
    sDict = "wald"      # The dictionary we are working for: wld, wbd, wald, wgd
    bUsdDbaseMijnen = False
    oErr = ErrHandle()

    def get_basename(d, s, a):
        # Basename: derive from deel/section/aflevering
        sBaseName = "fixture-d" + str(d)
        if iSectie != None: sBaseName = sBaseName + "-s" + str(s)
        sBaseName = sBaseName + "-a" + str(a)
        return sBaseName

    try:
        # Retrieve the correct instance of the status object
        oStatus = Status.objects.filter(id=iStatus).first()
        oStatus.method = "db"
        oStatus.set_status("preparing")
        
        # Other initialisations
        oBack['result'] = False
        if str(iDeel).isnumeric(): iDeel = int(iDeel)
        if str(iSectie).isnumeric(): iSectie = int(iSectie)
        if str(iAflevering).isnumeric(): iAflevering = int(iAflevering)

        bDoEverything = (iDeel == 0 and iSectie == 0 and iAflevering == 0)
        lstInfo = []

        if bDoEverything:
            # Special method: treat all the files under 'xlsx_files'
            for oInfo in Info.objects.all():
                lstInfo.append(oInfo)
        else:
            # Validate: input file exists
            if not "/" in xlsx_file and not "\\" in xlsx_file:
                xlsx_file = os.path.abspath( os.path.join(MEDIA_ROOT, "csv_files", xlsx_file))
            elif xlsx_file.startswith("csv_files"):
                xlsx_file = os.path.abspath( os.path.join(MEDIA_ROOT, xlsx_file))
            if (not os.path.isfile(xlsx_file)): 
                oStatus.set_status("error", "Cannot find file " + xlsx_file)
                return oBack

            # Get the [Info] object
            if iSectie == None or iSectie == "":
                oInfo = Info.objects.filter(deel=iDeel, aflnum=iAflevering).first()
            else:
                oInfo = Info.objects.filter(deel=iDeel, sectie=iSectie, aflnum=iAflevering).first()
            lstInfo.append(oInfo)

        # Start creating an array that will hold the fixture elements
        arFixture = []
        iPkLemma = 1        # The PK for each Lemma
        iPkDescr = 1        # The PK for each Description (lemma-toelichting many-to-many)
        iPkTrefwoord = 1    # The PK for each Trefwoord
        iPkDialect = 1      # The PK for each Dialect
        iPkEntry = 0        # The PK for each Entry
        iPkAflevering = 1   # The PK for each Aflevering
        iPkMijn = 1         # The PK for each Mijn
        iPkEntryMijn = 1    # The PK for each Entry/Mijn
        iCounter = 0        # Loop counter for progress
        iRead = 0           # Number read correctly
        iSkipped = 0        # Number skipped

        # Prepare the entry object
        oEntry = fEntry()

        # First check the presence of all the 'promised' files
        lMsg = []
        for oInfo in lstInfo:
            # Get the details of this object
            xlsx_file = oInfo.csv_file.path
            iDeel = oInfo.deel
            iSectie = oInfo.sectie
            iAflevering = oInfo.aflnum
            if not os.path.isfile(xlsx_file):
                lMsg.append("{}/{}/{} file is not existing: {}".format(
                    iDeel, iSectie, iAflevering, xlsx_file))
            elif oInfo.processed != None and oInfo.processed != "":
                # Check if there already is an output file name
                oErr.Status("Checking the PK of {}/{}/{}".format(iDeel, iSectie, iAflevering))
                sBaseName = get_basename(iDeel, iSectie, iAflevering)
                output_file = os.path.join(MEDIA_ROOT ,sBaseName + ".json")
                if os.path.isfile(output_file):
                    oErr.Status("Reading from file {}".format(output_file))
                    # Read the file as a JSON object
                    fl_out = io.open(output_file, "r", encoding='utf-8')   
                    lFix = json.load(fl_out)                 
                    # Find the highest (=last) 
                    size = len(lFix)
                    pk_last = lFix[size-1]['pk']
                    if pk_last > iPkEntry:
                        oErr.Status("Found last_pk to be {}".format(pk_last))
                        iPkEntry = pk_last + 1

        # Any messages?
        if len(lMsg) > 0:
            sMsg = "\n".join(lMsg)
            oStatus.set_status("error", sMsg)
            oBack['result'] = False
            oBack['msg'] = sMsg
            oErr.Status(sMsg)
            return oBack

         # Initialization of 'last' items
        descr_this = None
               
        # Process all the objects in [lstInfo]
        for oInfo in lstInfo:
            # Get the details of this object
            xlsx_file = oInfo.csv_file.path
            iDeel = oInfo.deel
            iSectie = oInfo.sectie
            iAflevering = oInfo.aflnum
            sProcessed = ""
            if oInfo.processed != None:
                sProcessed = oInfo.processed

            # Determine whether we will process this item or not
            bDoThisItem = (sProcessed == "" and (iDeel>0 or iSectie>0 or iAflevering>0))

            if bDoThisItem:
                # Make sure 'NONE' sectie is turned into an empty string
                if iSectie == None: iSectie = ""

                iRead = 0           # Number read correctly
                iSkipped = 0        # Number skipped

                sWorking = "working {}/{}/{}".format(iDeel, iSectie, iAflevering)
                oStatus.set_status(sWorking)
                oErr.Status(sWorking)

                # Create an output file writer
                # Basename: derive from deel/section/aflevering
                sBaseName = get_basename(iDeel, iSectie, iAflevering)
                output_file = os.path.join(MEDIA_ROOT ,sBaseName + ".json")
                skip_file = os.path.join(MEDIA_ROOT, sBaseName + ".skip")
                oFix = FixOut(output_file)
                oSkip = FixSkip(skip_file)

                # get a Aflevering number
                if str(iDeel).isnumeric(): iDeel = int(iDeel)
                if str(iSectie).isnumeric(): iSectie = int(iSectie)
                if str(iAflevering).isnumeric(): iAflevering = int(iAflevering)
                lstQ = []
                lstQ.append(Q(deel__nummer=iDeel))
                lstQ.append(Q(aflnum=iAflevering))
                if iSectie != None and iSectie != "":
                    lstQ.append(Q(sectie=iSectie))
                oAfl = Aflevering.objects.filter(*lstQ).first()
                iPkAflevering = oAfl.pk

                # Initialisations
                bEnd = False
                bFirst = True

                # Speed-up storages
                sLastLemma = ""    
                sLastLemmaDescr = ""
                sLastTw = ""
                sLastTwToel = ""
                # Instances
                lemma_this = None

                # The use of 'mijnen' depends on the dictionary we are working for (wld, wbd)
                lMijnen = []
                if sDict == "wld":
                    # The WLD uses mijnen in 2/5
                    bDoMijnen = (iDeel == 2 and iAflevering == 5)   # Treat 'Mijn' for wbd-II-5
                else:
                    # The WBD, WGD, WALD do NOT have any mijnen
                    bDoMijnen = False

                # Time measurements: keep track of time used in different parts
                oTime = {}
                oTime['read'] = 0   # time to read the XML file
                oTime['db'] = 0     # Time spent in reading and saving database items
                oTime['entry'] = 0  # Processing entries
                oTime['save'] = 0   # Time spent in saving
                oTime['search_L'] = 0   # Time spent in searching (lemma)
                oTime['search_T'] = 0   # Time spent in searching (trefwoord)
                oTime['search_Ds'] = 0  # Time spent in searching (description)
                oTime['search_Dt'] = 0  # Time spent in searching (dialect)
                oTime['search_LD'] = 0  # Time spent in searching (lemmadescription)
                oTime['search_M'] = 0   # Time spent in searching (mijn)

                # Now read the EXCEL as an object
                iStarttime = get_now_time()
                # Open the Excel file
                oProc = WgdProcessor(xlsx_file)
                oTime['read'] = get_now_time() - iStarttime
                iStartTime = get_now_time()

                # Iterate through all the rows
                while not bEnd:
                    # Read the row
                    oRow = oProc.next_row()
                    # Check if row is valid
                    if not oProc.is_valid():
                        bEnd = True
                        break
                    # Get the row number
                    row = oProc.row
                    # Perform part-to-line
                    oLine = oProc.partToLine()
                    # Check if this line contains 'valid' data:
                    iValid = isLineOkay(oLine)
                    # IF this is the first line or an empty line, then skip
                    if iValid == 0:
                        # Assuming this 'part' is entering an ENTRY

                        # Make sure we got TREFWOORD correctly
                        sTrefWoord = oLine['trefwoord_name']

                        if bDoMijnen and 'mijn_list' in oLine:
                            lMijnen = oLine['mijn_list']

                        # Try to do all of this within one actual transation
                        iStarttime = get_now_time()
                        with transaction.atomic():
                            # Find out which lemma this is
                            sLemma = oLine['lemma_name']
                            if sLemma != sLastLemma:
                                lemma_this = Lemma.get_instance({'gloss': sLemma}, oTime)
                                sLastLemma = sLemma

                            # Find out which lemma-description this is
                            descr_this = Description.get_instance({'bronnenlijst': oLine['lemma_bronnenlijst'],
                                                                'toelichting': oLine['lemma_toelichting'], 
                                                                'boek': oLine['lemma_boek']}, descr_this, oTime)

                            # We do need the PKs of the lemma and the description
                            iPkLemma = lemma_this.pk
                            iPkDescr = descr_this.pk

                            # Add the [iPkDescr] to the LemmaDescr--but only if it is not already there
                            iPkLemmaDescr = LemmaDescr.get_item({'lemma': lemma_this,
                                                                    'description': descr_this}, oTime)

                            # Find out which dialect this is
                            if oLine['dialect_kloeke'] != None and oLine['dialect_kloeke'] != "":
                                iPkDialect = Dialect.get_item({'stad': oLine['dialect_stad'], 
                                                                'nieuw': oLine['dialect_nieuw'],
                                                                'code': oLine['dialect_kloeke']}, oTime)
                                # Note: removed 'dialect_toelichting' in accordance with issue #22 of WLD
                            else:
                                iPkDialect = Dialect.get_item({'stad': oLine['dialect_stad'], 
                                                                'nieuw': oLine['dialect_nieuw']}, oTime)

                            # Find out which trefwoord this is
                            sTwToel = oLine['trefwoord_toelichting']
                            if sTwToel == None or sTwToel == "":
                                if sLastTwToel != "" or sLastTw != sTrefWoord:
                                    iPkTrefwoord = Trefwoord.get_item({'woord': sTrefWoord}, oTime)
                                    sLastTw = sTrefWoord
                                    sLastTwToel = ""
                            else:
                                if sLastTw != sTrefWoord or sLastTwToel != sTwToel:
                                    iPkTrefwoord = Trefwoord.get_item({'woord': sTrefWoord,
                                                                    'toelichting': sTwToel}, oTime)
                                    sLastTw = sTrefWoord
                                    sLastTwToel = sTwToel
                        oTime['db'] += get_now_time() - iStarttime

                        # Check validity
                        if iPkDescr < 0 or iPkLemma < 0 or iPkLemmaDescr < 0 or iPkDialect < 0 or iPkTrefwoord < 0:
                            # Something has gone wrong: we cannot continue
                            oStatus.set_status("error")
                            errHandle.DoError("csv_to_fixture has a negative index", True)
                            return oBack

                        # Process the ENTRY
                        sDialectWoord = oLine['dialectopgave_name']
                        # WGD-specific
                        sSubvraag = oLine['subvraag']
                        sInWoordenboek = "true" if oLine['inwoordenboek'] == "ja" else "false"
                        sComment = oLine['opmerking']
                        # Make sure that I use my OWN continuous [pk] for Entry
                        iPkEntry += 1
                        # Do *NOT* use the Entry PK that is returned 
                        iStarttime = get_now_time()
                        iDummy = oFix.get_pk(oEntry, "dictionary.entry", False,
                                                pk=iPkEntry,
                                                woord=sDialectWoord,
                                                toelichting=oLine['dialectopgave_toelichting'],
                                                kloeketoelichting=oLine['dialectopgave_kloeketoelichting'],
                                                lemma=iPkLemma,
                                                descr=iPkDescr,     # This is the Description that in principle is valid for the whole lemma, but not in practice
                                                dialect=iPkDialect,
                                                trefwoord=iPkTrefwoord,
                                                subvraag=sSubvraag,
                                                inwoordenboek=sInWoordenboek,
                                                opmerking=sComment,
                                                aflevering=iPkAflevering)
                        oTime['entry'] += get_now_time() - iStarttime

                        if bDoMijnen:
                            # Walk all the mijnen for this entry
                            for sMijn in lMijnen:
                                # Get the PK for this mijn
                                iPkMijn = Mijn.get_item({'naam': sMijn}, oTime)
                                # Process the PK for EntryMijn
                                iPkEntryMijn = EntryMijn.get_item({'entry': iPkEntry,
                                                                    'mijn': iPkMijn})

                        iRead += 1
                    else:
                        # This line is being skipped
                        oSkip.append(oProc.line())
                        iSkipped += 1
                        sIdx = 'line-' + str(iValid)
                        if not sIdx in oBack:
                            oBack[sIdx] = 0
                        oBack[sIdx] +=1
                    # Keep track of progress
                    oStatus.skipped = iSkipped
                    oStatus.read = iRead
                    oStatus.status = "{} (read={:.1f}, db={:.1f}, entry={:.1f}, search (L={:.1f}, T={:.1f}, Ds={:.1f}, LD={:.1f}, Dt={:.1f}, M={:.1f}), save={:.1f})".format(
                        sWorking, oTime['read'], oTime['db'], oTime['entry'],
                        oTime['search_L'], oTime['search_T'], oTime['search_Ds'], oTime['search_LD'], oTime['search_Dt'], oTime['search_M'], oTime['save'])
                    oStatus.save()


                # Close the skip file
                oSkip.close()

                # Finish the JSON array that contains the fixtures
                oFix.close()

                # Note the results for this info object
                oInfo.read = iRead
                oInfo.skipped = iSkipped
                oInfo.processed = "Processed at {:%d/%b/%Y %H:%M:%S}".format(datetime.now())
                oInfo.save()

        # return positively
        oBack['result'] = True
        oBack['skipped'] = iSkipped
        oBack['read'] = iRead
        oStatus.set_status("done")
        return oBack
    except:
        if oStatus != None:
            oStatus.set_status("error")
        sMsg = oErr.get_error_message()
        oErr.DoError("excel_to_fixture", True)
        return oBack

# ----------------------------------------------------------------------------------
# Name :    csv_to_fixture
# Goal :    Convert CSV file into a fixtures file
# History:
#  1/dec/2016   ERK Created
# ----------------------------------------------------------------------------------
def csv_to_fixture(csv_file, iDeel, iSectie, iAflevering, iStatus, bUseDbase=False, bUseOld=False):
    """Process a CSV with entry definitions"""

    oBack = {}      # What we return
    sVersie = ""    # The version we are using--this depends on the column names
    sDict = "wgd"   # The dictionary we are working for: wld, wbd, wgd
    bUsdDbaseMijnen = False
    # bUsdDbaseMijnen = True
    oErr = ErrHandle()

    def get_basename(d, s, a):
        # Basename: derive from deel/section/aflevering
        sBaseName = "fixture-d" + str(d)
        if iSectie != None: sBaseName = sBaseName + "-s" + str(s)
        sBaseName = sBaseName + "-a" + str(a)
        return sBaseName

    try:
        # Retrieve the correct instance of the status object
        oStatus = Status.objects.filter(id=iStatus).first()
        oStatus.status = "preparing"
        if bUseDbase:
            oStatus.method = "db"
        else:
            oStatus.method = "lst"
        # Save the status to the database
        oStatus.save()

        oBack['result'] = False

        if str(iDeel).isnumeric(): iDeel = int(iDeel)
        if str(iSectie).isnumeric(): iSectie = int(iSectie)
        if str(iAflevering).isnumeric(): iAflevering = int(iAflevering)

        bDoEverything = (iDeel == 0 and iSectie == 0 and iAflevering == 0)
        lstInfo = []

        if bDoEverything:
            # Special method: treat all the files under 'csv_files'
            for oInfo in Info.objects.all().order_by('deel', 'sectie', 'aflnum'):
                lstInfo.append(oInfo)
        else:
            # Validate: input file exists
            if not "/" in csv_file and not "\\" in csv_file:
                csv_file = os.path.abspath( os.path.join(MEDIA_ROOT, "csv_files", csv_file))
            elif csv_file.startswith("csv_files"):
                csv_file = os.path.abspath( os.path.join(MEDIA_ROOT, csv_file))
            if (not os.path.isfile(csv_file)): 
                oStatus.set_status("error", "Cannot find file " + csv_file)
                return oBack

            # Get the [Info] object
            if iSectie == None or iSectie == "":
                oInfo = Info.objects.filter(deel=iDeel, aflnum=iAflevering).first()
            else:
                oInfo = Info.objects.filter(deel=iDeel, sectie=iSectie, aflnum=iAflevering).first()
            lstInfo.append(oInfo)

        # Start creating an array that will hold the fixture elements
        arFixture = []
        iPkLemma = 1        # The PK for each Lemma
        iPkDescr = 1        # The PK for each Description (lemma-toelichting many-to-many)
        iPkTrefwoord = 1    # The PK for each Trefwoord
        iPkDialect = 1      # The PK for each Dialect
        iPkEntry = 0        # The PK for each Entry
        iPkAflevering = 1   # The PK for each Aflevering
        iPkMijn = 1         # The PK for each Mijn
        iPkEntryMijn = 1    # The PK for each Entry/Mijn
        iCounter = 0        # Loop counter for progress
        iRead = 0           # Number read correctly
        iSkipped = 0        # Number skipped

        # Prepare the entry object
        oEntry = fEntry()

        # Create instances of the Lemma, Dialect and other classes
        if not bUseDbase:
            oLemma = fLemma()
            oDescr = fDescr()
            oLemmaDescr = fLemmaDescr()
            oDialect = fDialect()
            oTrefwoord = fTrefwoord()
            oAflevering = fAflevering()
            oMijn = fMijn()
            oEntryMijn = fEntryMijn()

            # Initialise the lists in these instances (where needed)
            oDialect.load(Dialect.objects.all())
            oAflevering.load(Aflevering.objects.all())
            oMijn.load(Mijn.objects.all())
            if bUseOld:
                # Indicate we are loading existing stuff

                # Start loading...
                oStatus.set_status("loading lemma's")
                oLemma.load(Lemma.objects.all())

                oStatus.set_status("loading keywords")
                oTrefwoord.load(Trefwoord.objects.all())

                iSize = LemmaDescr.objects.all().count()
                oStatus.set_status("loading {} lemma-descriptions ".format(iSize))
                oLemmaDescr.load(LemmaDescr.objects.all())

                oStatus.set_status("loading descriptions")
                oDescr.load(Description.objects.all())
                # It should *not* be necessary to load all existing ENTRY objects
                #    since we assume that any object to be added is UNIQUE
                # oEntry.load(Entry.objects.all())
                oStatus.set_status("loading mines")
                oEntryMijn.load(EntryMijn.objects.all())

        if bUseOld:
            # Determine what the maximum [pk] for [Entry] currently in use is
            if Entry.objects.all().count() == 0:
                iPkEntry = 0
            else:
                iPkEntry = Entry.objects.latest('id').id

        # First check the presence of all the 'promised' files
        lMsg = []
        for oInfo in lstInfo:
            # Get the details of this object
            csv_file = oInfo.csv_file.path
            iDeel = oInfo.deel
            iSectie = oInfo.sectie
            iAflevering = oInfo.aflnum
            if not os.path.isfile(csv_file):
                lMsg.append("{}/{}/{} file is not existing: {}".format(
                    iDeel, iSectie, iAflevering, csv_file))
            elif oInfo.processed != None and oInfo.processed != "":
                # Check if there already is an output file name
                oErr.Status("Checking the PK of {}/{}/{}".format(iDeel, iSectie, iAflevering))
                sBaseName = get_basename(iDeel, iSectie, iAflevering)
                output_file = os.path.join(MEDIA_ROOT ,sBaseName + ".json")
                if os.path.isfile(output_file):
                    oErr.Status("Reading from file {}".format(output_file))
                    # Read the file as a JSON object
                    fl_out = io.open(output_file, "r", encoding='utf-8')   
                    lFix = json.load(fl_out)                 
                    # Find the highest (=last) 
                    size = len(lFix)
                    pk_last = lFix[size-1]['pk']
                    if pk_last > iPkEntry:
                        oErr.Status("Found last_pk to be {}".format(pk_last))
                        iPkEntry = pk_last + 1

        # Any messages?
        if len(lMsg) > 0:
            sMsg = "\n".join(lMsg)
            oStatus.set_status("error", sMsg)
            oBack['result'] = False
            oBack['msg'] = sMsg
            oErr.Status(sMsg)
            return oBack

         # Initialization of 'last' items
        descr_this = None
               
        # Process all the objects in [lstInfo]
        for oInfo in lstInfo:
            # Get the details of this object
            csv_file = oInfo.csv_file.path
            iDeel = oInfo.deel
            iSectie = oInfo.sectie
            iAflevering = oInfo.aflnum
            sProcessed = ""
            if oInfo.processed != None:
                sProcessed = oInfo.processed

            # Determine whether we will process this item or not
            bDoThisItem = (sProcessed == "" and (iDeel>0 or iSectie>0 or iAflevering>0))

            if bDoThisItem:
                # Make sure 'NONE' sectie is turned into an empty string
                if iSectie == None: iSectie = ""

                iRead = 0           # Number read correctly
                iSkipped = 0        # Number skipped

                sWorking = "working {}/{}/{}".format(iDeel, iSectie, iAflevering)
                oStatus.set_status(sWorking)
                oErr.Status(sWorking)

                # Create an output file writer
                # Basename: derive from deel/section/aflevering
                sBaseName = get_basename(iDeel, iSectie, iAflevering)
                output_file = os.path.join(MEDIA_ROOT ,sBaseName + ".json")
                skip_file = os.path.join(MEDIA_ROOT, sBaseName + ".skip")
                oFix = FixOut(output_file)
                oSkip = FixSkip(skip_file)

                # get a Aflevering number
                if str(iDeel).isnumeric(): iDeel = int(iDeel)
                if str(iSectie).isnumeric(): iSectie = int(iSectie)
                if str(iAflevering).isnumeric(): iAflevering = int(iAflevering)
                lstQ = []
                lstQ.append(Q(deel__nummer=iDeel))
                lstQ.append(Q(aflnum=iAflevering))
                if iSectie != None and iSectie != "":
                    lstQ.append(Q(sectie=iSectie))
                oAfl = Aflevering.objects.filter(*lstQ).first()
                iPkAflevering = oAfl.pk

                # Open source file to read line-by-line
                f = codecs.open(csv_file, "r", encoding='utf-8-sig')
                bEnd = False
                bFirst = True
                bFirstOut = False

                sVersie = ""
                sLastLemma = ""     # For speeding up processing
                sLastLemmaDescr = ""
                sLastTw = ""
                sLastTwToel = ""

                # The use of 'mijnen' depends on the dictionary we are working for (wld, wbd, wgd)
                lMijnen = []
                if sDict == "wld":
                    # The WLD uses mijnen in 2/5
                    bDoMijnen = (iDeel == 2 and iAflevering == 5)   # Treat 'Mijn' for wld-II-5
                else:
                    # The WGD doesn't have any mijnen
                    bDoMijnen = False

                # Time measurements: keep track of time used in different parts
                oTime = {}
                oTime['read'] = 0   # time to read the source file
                oTime['db'] = 0     # Time spent in reading and saving database items
                oTime['entry'] = 0  # Processing entries
                oTime['save'] = 0   # Time spent in saving
                oTime['search_L'] = 0   # Time spent in searching (lemma)
                oTime['search_T'] = 0   # Time spent in searching (trefwoord)
                oTime['search_Ds'] = 0  # Time spent in searching (description)
                oTime['search_Dt'] = 0  # Time spent in searching (dialect)
                oTime['search_LD'] = 0  # Time spent in searching (lemmadescription)
                oTime['search_M'] = 0   # Time spent in searching (mijn)

                # Iterate through the lines of the CSV file
                while (not bEnd):
                    # Show where we are
                    iCounter +=1
                    if iCounter % 1000 == 0:
                        errHandle.Status("Processing: " + str(iCounter))
                    # Read one line
                    iStarttime = get_now_time()
                    strLine = f.readline()
                    if (strLine == ""):
                        bEnd = True
                        break
                    strLine = str(strLine)
                    strLine = strLine.strip(" \n\r")
                    oTime['read'] += get_now_time() - iStarttime
                    # Only process substantial lines
                    if (strLine != ""):
                        # Split the line into parts
                        arPart = strLine.split('\t')
                        # Sanity check (Note: '7' is arbitrarily)
                        if len(arPart) < 7:
                            # Line is too short, so cannot be taken into consideration
                            iValid = 0
                        else:
                            # Convert the array of values to a structure
                            oLine = partToLine(sVersie, arPart, bDoMijnen)
                            # Check if this line contains 'valid' data:
                            iValid = isLineOkay(oLine)
                        # IF this is the first line or an empty line, then skip
                        if bFirst:
                            # Get the version from cell 0, line 0
                            sVersie = arPart[1]     # Assuming that the first field is [recordId]
                            # Check if the line starts correctly
                            if sVersie != 'Lemmanummer' and sVersie != "lemma.name":
                                # The first line does not start correctly -- return false
                                oErr.DoError("csv_to_fixture: cannot process version [{}] line=[{}], [{}]".format(sVersie, arPart[0], arPart[1]))
                                return oBack
                            # Indicate that the first item has been had
                            bFirst = False
                        elif iValid == 0:
                            # Assuming this 'part' is entering an ENTRY

                            # Make sure we got TREFWOORD correctly
                            sTrefWoord = oLine['trefwoord_name']

                            if bDoMijnen and 'mijn_list' in oLine:
                                lMijnen = oLine['mijn_list']


                            if bUseDbase:
                                # Try to do all of this within one actual transation
                                iStarttime = get_now_time()
                                with transaction.atomic():
                                    # Find out which lemma this is
                                    sLemma = oLine['lemma_name']
                                    if sLemma != sLastLemma:
                                        lemma_this = Lemma.get_instance({'gloss': sLemma}, oTime)
                                        sLastLemma = sLemma

                                    # Find out which lemma-description this is
                                    descr_this = Description.get_instance({'bronnenlijst': oLine['lemma_bronnenlijst'],
                                                                     'toelichting': oLine['lemma_toelichting'], 
                                                                     'boek': oLine['lemma_boek']}, descr_this, oTime)

                                    # We do need the PKs of the lemma and the description
                                    iPkLemma = lemma_this.pk
                                    iPkDescr = descr_this.pk

                                    # Add the [iPkDescr] to the LemmaDescr--but only if it is not already there
                                    iPkLemmaDescr = LemmaDescr.get_item({'lemma': lemma_this,
                                                                         'description': descr_this}, oTime)

                                    # Find out which dialect this is
                                    if oLine['dialect_kloeke'] != None and oLine['dialect_kloeke'] != "":
                                        iPkDialect = Dialect.get_item({'stad': oLine['dialect_stad'], 
                                                                        'nieuw': oLine['dialect_nieuw'],
                                                                        'code': oLine['dialect_kloeke']}, oTime)
                                        # Note: removed 'dialect_toelichting' in accordance with issue #22 of WLD
                                    else:
                                        iPkDialect = Dialect.get_item({'stad': oLine['dialect_stad'], 
                                                                        'nieuw': oLine['dialect_nieuw']}, oTime)

                                    # Find out which trefwoord this is
                                    sTwToel = oLine['trefwoord_toelichting']
                                    if sTwToel == None or sTwToel == "":
                                        if sLastTwToel != "" or sLastTw != sTrefWoord:
                                            iPkTrefwoord = Trefwoord.get_item({'woord': sTrefWoord}, oTime)
                                            sLastTw = sTrefWoord
                                            sLastTwToel = ""
                                    else:
                                        if sLastTw != sTrefWoord or sLastTwToel != sTwToel:
                                            iPkTrefwoord = Trefwoord.get_item({'woord': sTrefWoord,
                                                                           'toelichting': sTwToel}, oTime)
                                            sLastTw = sTrefWoord
                                            sLastTwToel = sTwToel
                                oTime['db'] += get_now_time() - iStarttime

                            else:
                                # Get a lemma number from this
                                iStarttime = get_now_time()
                                # NOTE: assume 2 = toelichting 
                                iPkLemma = oFix.get_pk(oLemma, "dictionary.lemma", True,
                                                       gloss=oLine['lemma_name'])

                                # Get a description number
                                iPkDescr = oFix.get_pk(oDescr, "dictionary.description", True,
                                                       bronnenlijst=oLine['lemma_bronnenlijst'], 
                                                       toelichting=oLine['lemma_toelichting'], 
                                                       boek=oLine['lemma_boek'])

                                # Add the Lemma-Description connection
                                iPkLemmaDescr = oFix.get_pk(oLemmaDescr, "dictionary.lemmadescr", True,
                                                            lemma=iPkLemma,
                                                            description=iPkDescr)


                                # get a dialect number
                                if oLine['dialect_kloeke'] != None:
                                    iPkDialect = oFix.get_pk(oDialect, "dictionary.dialect", True,
                                                             stad=oLine['dialect_stad'], 
                                                             nieuw=oLine['dialect_nieuw'],
                                                             code=oLine['dialect_kloeke'])
                                    # Note: removed 'dialect_toelichting' in accordance with issue #22 of WLD
                                else:
                                    iPkDialect = oFix.get_pk(oDialect, "dictionary.dialect", True,
                                                             stad=oLine['dialect_stad'], 
                                                             nieuw=oLine['dialect_nieuw'])

                                # get a trefwoord number
                                sTwToel = oLine['trefwoord_toelichting']
                                if sTwToel == None or sTwToel == "":
                                    iPkTrefwoord = oFix.get_pk(oTrefwoord, "dictionary.trefwoord", True,
                                                               woord=sTrefWoord)
                                else:
                                    iPkTrefwoord = oFix.get_pk(oTrefwoord, "dictionary.trefwoord", True,
                                                               woord=sTrefWoord,
                                                               toelichting=sTwToel)
                                # Keep track of the time
                                oTime['db'] += get_now_time() - iStarttime
                            # Check validity
                            if iPkDescr < 0 or iPkLemma < 0 or iPkLemmaDescr < 0 or iPkDialect < 0 or iPkTrefwoord < 0:
                                # Something has gone wrong: we cannot continue
                                oStatus.set_status("error")
                                errHandle.DoError("csv_to_fixture has a negative index", True)
                                return oBack

                            # Process the ENTRY
                            sDialectWoord = oLine['dialectopgave_name']
                            # Make sure that I use my OWN continuous [pk] for Entry
                            iPkEntry += 1
                            # Do *NOT* use the Entry PK that is returned 
                            iStarttime = get_now_time()
                            iDummy = oFix.get_pk(oEntry, "dictionary.entry", False,
                                                   pk=iPkEntry,
                                                   woord=sDialectWoord,
                                                   toelichting=oLine['dialectopgave_toelichting'],
                                                   kloeketoelichting=oLine['dialectopgave_kloeketoelichting'],
                                                   lemma=iPkLemma,
                                                   descr=iPkDescr,     # This is the Description that in principle is valid for the whole lemma, but not in practice
                                                   dialect=iPkDialect,
                                                   trefwoord=iPkTrefwoord,
                                                   aflevering=iPkAflevering)
                            oTime['entry'] += get_now_time() - iStarttime

                            if bDoMijnen:
                                if bUseDbase and bUsdDbaseMijnen:
                                    # Walk all the mijnen for this entry
                                    for sMijn in lMijnen:
                                        # Get the PK for this mijn
                                        iPkMijn = Mijn.get_item({'naam': sMijn}, oTime)
                                        # Process the PK for EntryMijn
                                        iPkEntryMijn = EntryMijn.get_item({'entry': iPkEntry,
                                                                           'mijn': iPkMijn})

                                else:
                                    # Walk all the mijnen for this entry
                                    for sMijn in lMijnen:
                                        # Get the PK for this mijn
                                        iPkMijn = oFix.get_pk(oMijn, "dictionary.mijn", True,
                                                              naam=sMijn)
                                        # Process the PK for EntryMijn
                                        iPkEntryMijn = oFix.get_pk(oEntryMijn, "dictionary.entrymijn", False,
                                                                   pk=iPkEntryMijn,
                                                                   entry=iPkEntry,
                                                                   mijn=iPkMijn)
                            iRead += 1
                        else:
                            # This line is being skipped
                            oSkip.append(strLine)
                            iSkipped += 1
                            sIdx = 'line-' + str(iValid)
                            if not sIdx in oBack:
                                oBack[sIdx] = 0
                            oBack[sIdx] +=1
                    # Keep track of progress
                    oStatus.skipped = iSkipped
                    oStatus.read = iRead
                    oStatus.status = "{} (read={:.1f}, db={:.1f}, entry={:.1f}, search (L={:.1f}, T={:.1f}, Ds={:.1f}, LD={:.1f}, Dt={:.1f}, M={:.1f}), save={:.1f})".format(
                        sWorking, oTime['read'], oTime['db'], oTime['entry'],
                        oTime['search_L'], oTime['search_T'], oTime['search_Ds'], oTime['search_LD'], oTime['search_Dt'], oTime['search_M'], oTime['save'])
                    oStatus.save()


                # CLose the input file
                f.close()

                # Close the skip file
                oSkip.close()

                # Finish the JSON array that contains the fixtures
                oFix.close()

                # Note the results for this info object
                oInfo.read = iRead
                oInfo.skipped = iSkipped
                oInfo.processed = "Processed at {:%d/%b/%Y %H:%M:%S}".format(datetime.now())
                oInfo.save()

        # return positively
        oBack['result'] = True
        oBack['skipped'] = iSkipped
        oBack['read'] = iRead
        # oCsvImport['status'] = 'done'
        oStatus.set_status("done")
        return oBack
    except:
        # oCsvImport['status'] = 'error'
        oStatus.status = "error"
        oStatus.save()
        errHandle.DoError("csv_to_fixture", True)
        return oBack


def do_repair_kloeke(oRepair):
    """Upload kloeke-to-city definitions from TSV"""

    # The name of the file
    KLOEKE_FILE = "kloekecodes.tsv"

    oErr = ErrHandle()
    try:
        # Show we are starting
        oRepair.set_status("Starting up reading Kloeke code TSV")

        # Combine the file name
        fName = os.path.abspath(os.path.join(MEDIA_ROOT, KLOEKE_FILE))
        oBack = Kloeke.readcodes(fName, oRepair)

        # Check if there is an error
        if oBack == None or 'status' not in oBack or oBack['status'] != "ok":
            return False

        # Indicate we are ready
        oRepair.set_status("finished")

        # Return positively
        return True
    except:
        msg = oErr.get_error_message()
        oRepair.set_status("Error: {}".format(msg))
        return False



# ----------------------------------------------------------------------------------
# Name :    do_repair_lemma
# Goal :    Repair the lemma's
# History:
#  13/dec/2016   ERK Created
# ----------------------------------------------------------------------------------
def do_repair_lemma(oRepair):
    """Repair lemma stuff"""

    # Get all the lemma's
    qs = Lemma.objects.all()

    # Walk all the lemma's
    iStart = 0
    iLen = qs.count()
    iRepair = 0
    for oLem in qs:
        # Note progress
        iStart += 1
        bChange = False
        # Show where we are
        oRepair.status = "Working on {} (of {})".format(iStart,iLen)
        oRepair.save()
        # Remove spaces from lemma
        sGloss = oLem.gloss.strip()
        if sGloss != oLem.gloss:
            iRepair +=1
            oLem.gloss = sGloss
            bChange = True
        # Check for trailing and following quotation marks
        sGloss = oLem.gloss
        if sGloss.startswith('"') and sGloss.endswith('"'):
            oLem.gloss = sGloss.strip('"')
            iRepair += 1
            bChange = True
        sGloss = oLem.gloss
        if sGloss.startswith("'") and sGloss.endswith("'"):
            oLem.gloss = sGloss.strip("'")
            iRepair += 1
            bChange = True
        # Have any changes been made?
        if bChange:
            # save the changes
            oLem.save()
            oRepair.status = "Saved changes in {} (of {})".format(iStart,iLen)
            oRepair.save()

    # Return positively
    return True

def do_repair_clean(oRepair):
    """Clean the database from Entry, Lemma, Trefwoord contents"""

    oErr = ErrHandle()
    try:
        # Show we are starting
        oRepair.set_status("Starting up Cleaning of Lemma/Trefwoord/Entry")

        # (1) clean LemmaDescr
        oRepair.set_status("Step 1: LemmaDescr...")
        qs = LemmaDescr.objects.all()
        with transaction.atomic():
            qs.delete()

        # (2) clean EntryMijn
        oRepair.set_status("Step 2: EntryMijn...")
        qs = EntryMijn.objects.all()
        with transaction.atomic():
            qs.delete()

        # (3) clean Entry
        oRepair.set_status("Step 3: Entry...")
        qs = Entry.objects.all()
        with transaction.atomic():
            qs.delete()

        # (4) clean Lemma
        oRepair.set_status("Step 4: Lemma...")
        qs = Lemma.objects.all()
        with transaction.atomic():
            qs.delete()

        # (5) clean LemmaDescr
        oRepair.set_status("Step 5: Trefwoord...")
        qs = Trefwoord.objects.all()
        with transaction.atomic():
            qs.delete()

        # (6) clean Dialect
        oRepair.set_status("Step 6: Dialect...")
        qs = Dialect.objects.all()
        with transaction.atomic():
            qs.delete()

        oRepair.set_status("Cleaning has finished")
        # Now we are ready
        return True
    except:
        msg = oErr.get_error_message()
        oRepair.set_status("Error: {}".format(msg))
        return False
    
def do_repair_entrydescr(oRepair):
    """Repair descriptions and the entries that point to them"""

    oErr = ErrHandle()
    try:
        # Show we are starting
        oRepair.status = "Starting up Repair-EntryDescr"
        oRepair.save()

        # Get all the entries ordered by description text
        # Note: do not use select_related(). because of the iterator
        qs = Entry.objects.all().order_by(
            'descr__toelichting',
            'descr__bronnenlijst',
            'descr__boek')

        # Start a list of descr objects that need to be deleted
        descr_del = []

        if qs.exists():
            # Prepare a 'previous' object
            oPrev = None
            entry_prev = None
            count = 0
            dCount = 0
            # Iterate over them
            for entry in qs.iterator():
                ## DEBUGGING
                #if entry.id == 1551778:
                #    iStop = True
                # show where we are
                if count % 1000 == 0:
                    oRepair.status = "Working on entry {}".format(count)
                    oRepair.save()
                # Get the new description values
                descr = entry.descr
                oNew = {'toelichting': descr.toelichting,
                        'bronnenlijst': descr.bronnenlijst}
                if descr.boek: 
                    oNew['boek'] = descr.boek
                else:
                    oNew['boek'] = None
                # Keep track of where we are
                count += 1
                # Check if this should be removed
                if oPrev != None and descr.id != descr_prev.id and oPrev['toelichting'] == oNew['toelichting'] and \
                   oPrev['bronnenlijst'] == oNew['bronnenlijst'] and oPrev['boek'] == oNew['boek']:
                    # Add this description to the deletables
                    if not descr.id in descr_del:
                        descr_del.append(descr.id)
                        dCount += 1
                    # Possibly change the lemmadescr
                    ld_list = LemmaDescr.objects.filter(description=descr)
                    with transaction.atomic():
                        # The new one is the same as the previous, so it should be added to the list of the ones that can be deleted
                        entry.descr = descr_prev
                        entry.save()
                        for ld in ld_list:
                            ld.description = descr_prev
                            ld.save()
                else:
                    oPrev = copy.copy(oNew)
                    descr_prev = descr

            # Now delete all necessary description objects
            oRepair.status = "Deleting descr instances: {}...".format(dCount)
            oRepair.save()
            # divide over chunks of 100
            n = 100
            for i in range(0, dCount, n):
                oRepair.status = "Deleting descr instances: {} chunk={}...".format(dCount, i)
                oRepair.save()
                chnk = descr_del[i:i+n]
                with transaction.atomic():
                    Description.objects.filter(id__in=chnk).delete()
            # Reset the list
            descr_del = []

        oRepair.status = "Everything has finished"
        oRepair.save()
        # Now we are ready
        return True
    except:
        msg = oErr.get_error_message()
        oRepair.status = "Error: {}".format(msg)
        oRepair.save()
        return False
