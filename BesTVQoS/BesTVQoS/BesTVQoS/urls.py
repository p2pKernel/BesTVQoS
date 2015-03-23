"""
Definition of urls for BesTVQoS.
"""

# from datetime import datetime
from django.conf.urls import patterns, url

# Uncomment the next lines to enable the admin:
# from django.conf.urls import include
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns(
    '',
    # Examples:
    url(r'^$', 'common.views.home'),
    url(r'^m/$', 'common.views.m_home'),

    url(r'^update/playinfo$', 'tplay.views.playinfo'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)