"""
Definition of urls for wald.
"""

from datetime import datetime
from django.contrib.auth.decorators import login_required, permission_required
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.contrib import admin
import django.contrib.auth.views
from django.views.decorators.csrf import csrf_exempt

# Enable the admin:
from wald.settings import APP_PREFIX, STATIC_ROOT

# Imports for the app 'dictionary'
import wald.dictionary.forms
from wald.dictionary.views import *
from wald.dictionary.adminviews import EntryListView, InfoListView

# Other Django stuff
from django.core import urlresolvers
from django.shortcuts import redirect
from django.core.urlresolvers import reverse, reverse_lazy
from django.views.generic.base import RedirectView
from django.views.generic import TemplateView

admin.autodiscover()

# set admin site names
admin.site.site_header = 'e-WALD Admin'
admin.site.site_title = 'e-WALD Site Admin'

pfx = APP_PREFIX

urlpatterns = [
    # Examples:
    url(r'^$', wald.dictionary.views.home, name='home'),
    url(r'^contact$', wald.dictionary.views.contact, name='contact'),
    url(r'^about', wald.dictionary.views.about, name='about'),
    url(r'^guide', wald.dictionary.views.guide, name='guide'),
    url(r'^robots.txt', TemplateView.as_view(template_name='dictionary/robots.txt', content_type='text/plain')),
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
    url(r'^locations', LocationListView.as_view(), name='locations'),
    url(r'^location/search/$', LocationListView.as_view(), name='locationsearch'),
    url(r'^mines', MijnListView.as_view(), name='mines'),
    url(r'^mine/search/$', MijnListView.as_view(), name='minesearch'),
    url(r'^list/$', permission_required('dictionary.search_gloss')(EntryListView.as_view()), name='admin_entry_list'), 
    url(r'^dictionary/search/$', permission_required('dictionary.search_gloss')(EntryListView.as_view())),
    url(r'^entry/(?P<pk>\d+)', DictionaryDetailView.as_view(), name='output'),

    url(r'^import/start/$', wald.dictionary.views.import_csv_start, name='import_start'),
    url(r'^import/progress/$', wald.dictionary.views.import_csv_progress, name='import_progress'),

    url(r'^import/update(?:/(?P<pk>\d+))?/start/$', wald.dictionary.views.import_update_start, name='import_update_start'),
    url(r'^import/update(?:/(?P<pk>\d+))?/progress/$', wald.dictionary.views.import_update_progress, name='import_update_progress'),

    url(r'^repair/$', permission_required('dictionary.search_gloss')(wald.dictionary.views.do_repair), name='repair'),
    url(r'^repair/start/$', wald.dictionary.views.do_repair_start, name='repair_start'),
    url(r'^repair/progress/$', wald.dictionary.views.do_repair_progress, name='repair_progress'),
    url(r'^static/(?P<path>.*)$',django.views.static.serve, {'document_root': STATIC_ROOT}),

    url(r'^signup/$', wald.dictionary.views.signup, name='signup'),

    url(r'^login/user/(?P<user_id>\w[\w\d_]+)$', wald.dictionary.views.login_as_user, name='login_as'),

    url(r'^login/$',
        django.contrib.auth.views.login,
        {
            'template_name': 'dictionary/login.html',
            'authentication_form': wald.dictionary.forms.BootstrapAuthenticationForm,
            'extra_context':
            {
                'title': 'Log in',
                'year': datetime.now().year,
            }
        },
        name='login'),
    url(r'^logout$',
        django.contrib.auth.views.logout,
        {
            'next_page': reverse_lazy('home'),
        },
        name='logout'),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls), name='admin_base'),
]
