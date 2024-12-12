from lambda_function_utils import *
import json


def lambda_handler(event, context):
    print("##### RECEIVED EVENT:", json.dumps(event))