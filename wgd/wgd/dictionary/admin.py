from django.contrib import admin
from django import forms
from django.core import serializers
from django.contrib.contenttypes.models import ContentType
from django.forms import TextInput
from wgd.dictionary.models import *
import logging

MAX_IDENTIFIER_LEN = 10
logger = logging.getLogger(__name__)

def remove_from_fieldsets(fieldsets, fields):
    for fieldset in fieldsets:
        for field in fields:
            if field in fieldset[1]['fields']:
                logging.debug("'%s' field found in %s, hiding." % (field, fieldset[1]['fields']))
                newfields = []
                for myfield in fieldset[1]['fields']:
                    if not myfield in fields:
                        newfields.append(myfield)

                fieldset[1]['fields'] = tuple(newfields)
                logger.debug('Setting newfields to: %s' % newfields)

                break

class FieldChoiceAdmin(admin.ModelAdmin):
    readonly_fields=['machine_value']
    list_display = ['english_name','dutch_name','abbr', 'machine_value','field']
    list_filter = ['field']

    def save_model(self, request, obj, form, change):

        if obj.machine_value == None:
            # Check out the query-set and make sure that it exists
            qs = FieldChoice.objects.filter(field=obj.field)
            if len(qs) == 0:
                # The field does not yet occur within FieldChoice
                # Future: ask user if that is what he wants (don't know how...)
                # For now: assume user wants to add a new field (e.g: wordClass)
                # NOTE: start with '0'
                obj.machine_value = 0
            else:
                # Calculate highest currently occurring value
                highest_machine_value = max([field_choice.machine_value for field_choice in qs])
                # The automatic machine value we calculate is 1 higher
                obj.machine_value= highest_machine_value+1

        obj.save()


class LemmaAdmin(admin.ModelAdmin):
    fieldsets = ( ('Editable', {'fields': ('gloss', )}),
                )
    list_display = ['gloss']
    search_fields = ['gloss']


class DescriptionAdmin(admin.ModelAdmin):
    fieldsets = ( ('Editable', {'fields': ('toelichting', 'bronnenlijst', 'boek',)}),
                )
    list_display = ['toelichting', 'bronnenlijst', 'boek']


class DialectAdmin(admin.ModelAdmin):
    fieldsets = ( ('Editable', {'fields': ('stad', 'code', 'nieuw', 'streek', 'coordinate', 'toonbaar',)}),
                )
    list_display = ['nieuw', 'stad', 'streek']
    search_fields = ['nieuw', 'stad']


class CoordinateAdmin(admin.ModelAdmin):
    fieldsets = ( ('Editable', {'fields': ('kloeke', 'country', 'province', 'dictionary', 'place', 'point',)}),
                )
    list_display = ['kloeke', 'country', 'province', 'dictionary', 'place', 'point']
    list_filter = ['country', 'province', 'dictionary']
    search_fields = ['place', 'province', 'country', 'kloeke']


class TrefwoordAdmin(admin.ModelAdmin):
    fieldsets = ( ('Editable', {'fields': ('woord', 'toelichting',)}),
                )
    list_display = ['woord', 'toelichting']


class EntryAdmin(admin.ModelAdmin):
    fieldsets = ( ('Editable', {'fields': ('woord', 'lemma', 'dialect', 'trefwoord', 'toelichting', 'kloeketoelichting', 'aflevering')}),
                )
    list_display = ['woord', 'lemma', 'dialect', 'trefwoord', 'toelichting', 'kloeketoelichting']
    list_filter = ['lemma', 'dialect']
    search_fields = ['woord', 'trefwoord__woord', 'lemma__gloss']


class AfleveringAdmin(admin.ModelAdmin):
    formfield_overrides = {
            models.CharField: {'widget': TextInput(attrs={'size': '50'})}
        }
    fieldsets = ( ('Editable', {'fields': ('naam', 'deel', 'sectie', 'aflnum', 'inleiding', 'toonbaar', 'jaar', 'auteurs',
                                           'afltitel', 'sectietitel', 'plaats', 'toelichting')}),
                )
    list_display = ['id', 'deel', 'sectie', 'aflnum', 'naam', 'inleiding', 'toonbaar']
    ordering = ['deel__nummer', 'sectie', 'aflnum']


def reset_infos(modeladmin, request, qs):
    """Reset all the info's in the queryset"""

    with transaction.atomic():
        for info in qs:
            info.reset_item()
reset_infos.short_description = "Reset process info"

def clean_infos(modeladmin, request, qs):
    """Reset all the info's in the queryset and remove associated CSV files"""

    with transaction.atomic():
        for info in qs:
            info.clear_item()
clean_infos.short_description = "Clean process Info and remove CSV files"

class InfoAdmin(admin.ModelAdmin):
    list_display = ['deel', 'sectie', 'aflnum', 'csv_file', 'processed', 'read', 'skipped']
    actions = [reset_infos, clean_infos]
    ordering = ['deel', 'sectie', 'aflnum']
    list_filter = ['deel', 'sectie']


class KloekeAdmin(admin.ModelAdmin):
    #list_display = ['code', 'stad', 'alt1', 'alt2']
    #search_fields = ['code', 'stad', 'alt1', 'alt2']
    #ordering = ['stad', 'code']

    list_display = ['code', 'oud',  'stad', 'alt1', 'alt2', 'numcode', 'numstad']
    search_fields = ['code','oud',  'stad', 'alt1', 'alt2']
    ordering = ['-numstad', 'stad', 'code', 'oud']
    list_filter = ['numcode', 'numstad']


# -- Components of an entry
admin.site.register(Lemma, LemmaAdmin)
admin.site.register(Dialect, DialectAdmin)
admin.site.register(Coordinate, CoordinateAdmin)
admin.site.register(Trefwoord, TrefwoordAdmin)
admin.site.register(Aflevering, AfleveringAdmin)
admin.site.register(Mijn)
admin.site.register(Info, InfoAdmin)
admin.site.register(Information)
admin.site.register(Description, DescriptionAdmin)

# -- Components of a publication
admin.site.register(Deel)

# -- dictionary as a whole
admin.site.register(Entry, EntryAdmin)

# -- Other
admin.site.register(FieldChoice, FieldChoiceAdmin)
admin.site.register(Kloeke, KloekeAdmin)
