from django.core.exceptions import ImproperlyConfigured
from ledger.settings_base import *

ROOT_URLCONF = 'wildlifecompliance.urls'
SITE_ID = 1

INSTALLED_APPS += [
    'bootstrap3',
    'wildlifecompliance',
    'wildlifecompliance.components.main',
    'wildlifecompliance.components.applications',
    'wildlifecompliance.components.organisations',
    'wildlifecompliance.components.licences',
    'wildlifecompliance.components.users',
    'wildlifecompliance.components.returns',
    'taggit',
    'rest_framework',
    'rest_framework_gis'
]

SITE_ID = 1

# maximum number of days allowed for a booking
WSGI_APPLICATION = 'wildlifecompliance.wsgi.application'

'''REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'wildlifecompliance.perms.OfficerPermission',
    )
}'''

MIDDLEWARE_CLASSES += [
    'wildlifecompliance.middleware.FirstTimeNagScreenMiddleware'
]

TEMPLATES[0]['DIRS'].append(os.path.join(BASE_DIR, 'wildlifecompliance', 'templates'))
TEMPLATES[0]['DIRS'].append(os.path.join(BASE_DIR, 'wildlifecompliance','components','organisations', 'templates'))
TEMPLATES[0]['DIRS'].append(os.path.join(BASE_DIR, 'wildlifecompliance','components','emails', 'templates'))
BOOTSTRAP3 = {
    'jquery_url': '//static.dpaw.wa.gov.au/static/libs/jquery/2.2.1/jquery.min.js',
    'base_url': '//static.dpaw.wa.gov.au/static/libs/twitter-bootstrap/3.3.6/',
    'css_url': None,
    'theme_url': None,
    'javascript_url': None,
    'javascript_in_head': False,
    'include_jquery': False,
    'required_css_class': 'required-form-field',
    'set_placeholder': False,
}
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.join(BASE_DIR, 'wildlifecompliance', 'cache'),
    }
}
STATICFILES_DIRS.append(os.path.join(os.path.join(BASE_DIR, 'wildlifecompliance', 'static')))
DEV_STATIC = env('DEV_STATIC',False)
DEV_STATIC_URL = env('DEV_STATIC_URL')
if DEV_STATIC and not DEV_STATIC_URL:
    raise ImproperlyConfigured('If running in DEV_STATIC, DEV_STATIC_URL has to be set')
DATA_UPLOAD_MAX_NUMBER_FIELDS = None 

# Department details
SYSTEM_EMAIL = env('SYSTEM_EMAIL','wildlifecompliance@dbca.wa.gov.au')
WC_PAYMENT_SYSTEM_ID = env('WC_PAYMENT_SYSTEM_ID', 'S999')
if not VALID_SYSTEMS:
    VALID_SYSTEMS = [WC_PAYMENT_SYSTEM_ID]
DEP_URL = env('DEP_URL','www.dbca.wa.gov.au')
DEP_PHONE = env('DEP_PHONE','(08) 9219 9831')
DEP_FAX = env('DEP_FAX','(08) 9423 8242')
DEP_POSTAL = env('DEP_POSTAL','Locked Bag 104, Bentley Delivery Centre, Western Australia 6983')
DEP_NAME = env('DEP_NAME','Department of Biodiversity, Conservation and Attractions')
SITE_URL = env('SITE_URL','https://wildlifecompliance-uat.dpaw.wa.gov.au')
