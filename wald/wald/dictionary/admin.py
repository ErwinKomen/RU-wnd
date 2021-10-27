from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.core import serializers
from django.contrib.contenttypes.models import ContentType
from django.forms import TextInput
from wald.dictionary.models import *
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
    fieldsets = ( ('Editable', {'fields': ('stad', 'code', 'nieuw', 'toonbaar',)}),
                )
    list_display = ['nieuw', 'stad']


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
    list_display = ['deelnummer', 'deel', 'sectie', 'aflnum', 'naam', 'inleiding', 'toonbaar']


class DeelAdmin(admin.ModelAdmin):
    formfield_overrides = {
            models.CharField: {'widget': TextInput(attrs={'size': '50'})}
        }
    list_display = ['nummer', 'titel']
    fields = ['nummer', 'titel', 'toelichting'] 


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


def reset_updates(modeladmin, request, qs):
    """Reset all the data update's in the queryset"""

    with transaction.atomic():
        for dataupdate in qs:
            dataupdate.reset_item()
reset_updates.short_description = "Reset processing DataUpdate"

def clean_updates(modeladmin, request, qs):
    """Reset all the data update's in the queryset and remove associated CSV/XML files"""

    with transaction.atomic():
        for dataupdate in qs:
            dataupdate.clear_item()
clean_updates.short_description = "Clean processing DataUpdate and remove CSV/XML files"


class DataUpdateAdmin(admin.ModelAdmin):
    list_display = ['id', 'csv_file', 'processed', 'read', 'skipped']
    actions = [reset_updates, clean_updates]
    ordering = ['csv_file']
    # list_filter = ['deel', 'sectie']


# -- Components of an entry
admin.site.register(Lemma, LemmaAdmin)
admin.site.register(Dialect, DialectAdmin)
admin.site.register(Coordinate, CoordinateAdmin)
admin.site.register(Trefwoord, TrefwoordAdmin)
admin.site.register(Aflevering, AfleveringAdmin)
admin.site.register(Mijn)
admin.site.register(Info, InfoAdmin)
admin.site.register(Information)
admin.site.register(DataUpdate, DataUpdateAdmin)
admin.site.register(Description, DescriptionAdmin)

# -- Components of a publication
admin.site.register(Deel, DeelAdmin)

# -- dictionary as a whole
admin.site.register(Entry, EntryAdmin)