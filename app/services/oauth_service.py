"""OAuth 2.0 social login infrastructure.
Configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars to enable.
"""
import os


def is_oauth_enabled():
    return bool(os.environ.get('GOOGLE_CLIENT_ID'))


def get_google_auth_url(redirect_uri):
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
    if not client_id:
        return None
    return (f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&redirect_uri={redirect_uri}"
            f"&response_type=code&scope=email%20profile")


def exchange_google_code(code, redirect_uri):
    """Exchange auth code for user info. Returns {email, name} or None."""
    import requests
    client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    if not client_id or not client_secret:
        return None
    try:
        token_resp = requests.post('https://oauth2.googleapis.com/token', data={
            'code': code, 'client_id': client_id, 'client_secret': client_secret,
            'redirect_uri': redirect_uri, 'grant_type': 'authorization_code'
        }, timeout=10)
        token_data = token_resp.json()
        access_token = token_data.get('access_token')
        if not access_token:
            return None
        user_resp = requests.get('https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}, timeout=10)
        user_data = user_resp.json()
        return {'email': user_data.get('email'), 'name': user_data.get('name')}
    except Exception:
        return None
