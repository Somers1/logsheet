import json
import os
import sys
from pathlib import Path

sys.path.append('/opt/python')

os.environ['DJANGO_SETTINGS_MODULE'] = f'logsheet.settings'
from django.core.handlers import APIGatewayHandler

handler = APIGatewayHandler()


def lambda_handler(event, context=None):
    response = handler(event, context)
    response_dict = {
        'statusCode': response.status_code,
        'headers': dict(response.headers),
    }
    if hasattr(response, 'data'):
        response_dict['body'] = json.dumps(response.data)
    return response_dict
