from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback


def api_exception_handler(exc, context):
    if isinstance(exc, IntegrityError):
        set_rollback()
        return Response({'code': 'integrity_conflict', 'message': 'A operação viola uma restrição de integridade.'}, status=409)
    response = exception_handler(exc, context)
    if response is not None:
        original = response.data
        response.data = {
            'code': getattr(exc, 'default_code', 'request_error'),
            'message': str(original.get('detail', 'Revise os dados enviados.')) if isinstance(original, dict) else 'Revise os dados enviados.',
            'errors': original,
            'request_id': getattr(context.get('request'), 'request_id', None),
        }
    return response
