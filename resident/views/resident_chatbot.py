from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from resident.chatbot import get_smart_response


@csrf_exempt
@require_http_methods(["POST"])
# @login_required
def chatbot_response(request):
    """
    Handle chatbot message requests and return AI responses
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({
                'success': False,
                'error': 'Message cannot be empty'
            }, status=400)
        
        # Get response from chatbot AI
        bot_response = get_smart_response(user_message)

        return JsonResponse({
            'success': True,
            'response': bot_response,
            'timestamp': str(request.user.date_joined) if hasattr(request.user, 'date_joined') else None
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON format'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while processing your request'
        }, status=500)
