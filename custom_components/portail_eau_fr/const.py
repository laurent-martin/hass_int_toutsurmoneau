'''Constants for water provider portal.'''

VERSION = '0.0.10'

# (HASS) same as in manifest.json
DOMAIN = 'portail_eau_fr'

# prefix of method name for steps
PREFIX_STEP = 'async_step_'
# the various form steps
STEP_USER_START = 'user'
STEP_GET_METER_ID = 'get_identifier'
STEP_IMPORT = 'import_history'
STEP_FINISH = 'finish'
STEP_INIT = 'init'

# form input fields
USER_INPUT_USERNAME = 'input_username'
USER_INPUT_PASSWORD = 'input_password'
USER_INPUT_URL = 'input_url'
USER_INPUT_METER_ID = 'input_meter_id'
