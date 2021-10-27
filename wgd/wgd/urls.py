"""
Definition of urls for wgd.
"""

from datetime import datetime
from django.contrib.auth.decorators import login_required, permission_required
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
import django.contrib.auth.views
from django.views.decorators.csrf import csrf_exempt

# Enable the admin:
from wgd.settings import APP_PREFIX, STATIC_ROOT

# Imports for the app 'dictionary'
import wgd.dictionary.forms
from wgd.dictionary.views import *
from wgd.dictionary.adminviews import EntryListView, InfoListView

# Other Django stuff
# from django.core import urlresolvers
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic.base import RedirectView
from django.views.generic import TemplateView

admin.autodiscover()

# set admin site names
admin.site.site_header = 'e-WGD Admin'
admin.site.site_title = 'e-WGD Site Admin'

pfx = APP_PREFIX

urlpatterns = [
    # Examples:
    url(r'^$', wgd.dictionary.views.home, name='home'),
    url(r'^contact$', wgd.dictionary.views.contact, name='contact'),
    url(r'^about', wgd.dictionary.views.about, name='about'),
    url(r'^guide', wgd.dictionary.views.guide, name='guide'),
    url(r'^robots.txt', TemplateView.as_view(template_name='dictionary/robots.txt', content_type='text/plain')),
    url(r'^api/kloeke$', wgd.dictionary.views.kloeke_plaats, name='kloeke_plaats'),
    url(r'^delen', DeelListView.as_view(), name='delen'),
    url(r'^definitions$', RedirectView.as_view(url='/'+pfx+'admin/'), name='definitions'),
    url(r'^entries$', RedirectView.as_view(url='/'+pfx+'admin/dictionary/entry/'), name='entries'),
    url(r'^entries/import/$', permission_required('dictionary.search_gloss')(InfoListView.as_view()), name='admin_import_list'),
    url(r'^lemmas$', LemmaListView.as_view(), name='lemmas'),
    url(r'^lemma/search/$', LemmaListView.as_view(), name='lemmasearch'),
    url(r'^lemma/search/ajax/$', LemmaListView.as_view(), name='lemmasearch_ajax'),
    url(r'^lemma/map/(?P<pk>\d+)/$', csrf_exempt(LemmaMapView.as_view()), name='lemmamap'),
    url(r'^trefwoord/search/$', TrefwoordListView.as_view(), name='trefwoordsearch'),
    url(r'^dialects', DialectListView.as_view(), name='dialects'),
    url(r'^dialect/search/$', DialectListView.as_view(), name='dialectsearch'),
    url(r'^dialect/check/$', DialectCheckView.as_view(), name='dialectcheck'),
    url(r'^dialect/map/$', csrf_exempt(DialectMapView.as_view()), name='dialectmap'),
    url(r'^kloeke/search/$', KloekeListView.as_view(), name='kloekecodes'),
    url(r'^locations', LocationListView.as_view(), name='locations'),
    url(r'^location/search/$', LocationListView.as_view(), name='locationsearch'),
    url(r'^mines', MijnListView.as_view(), name='mines'),
    url(r'^mine/search/$', MijnListView.as_view(), name='minesearch'),
    url(r'^list/$', permission_required('dictionary.search_gloss')(EntryListView.as_view()), name='admin_entry_list'), 
    url(r'^dictionary/search/$', permission_required('dictionary.search_gloss')(EntryListView.as_view())),
    url(r'^entry/(?P<pk>\d+)', DictionaryDetailView.as_view(), name='output'),
    url(r'^import/start/$', wgd.dictionary.views.import_csv_start, name='import_start'),
    url(r'^import/progress/$', wgd.dictionary.views.import_csv_progress, name='import_progress'),
    url(r'^repair/$', permission_required('dictionary.search_gloss')(wgd.dictionary.views.do_repair), name='repair'),
    url(r'^repair/start/$', wgd.dictionary.views.do_repair_start, name='repair_start'),
    url(r'^repair/progress/$', wgd.dictionary.views.do_repair_progress, name='repair_progress'),
    url(r'^static/(?P<path>.*)$',django.views.static.serve, {'document_root': STATIC_ROOT}),

    url(r'^login/$', LoginView.as_view
        (
            template_name= 'dictionary/login.html',
            authentication_form= wgd.dictionary.forms.BootstrapAuthenticationForm,
            extra_context= {'title': 'Log in','year': datetime.now().year,}
        ),
        name='login'),
    url(r'^logout$',  LogoutView.as_view(next_page=reverse_lazy('home')), name='logout'),

    # Uncomment the admin/doc line below to enable admin documentation:
    #url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', admin.site.urls, name='admin_base'),
]
