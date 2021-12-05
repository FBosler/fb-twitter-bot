import tweepy
from bots.config import get_config

__API = None


def configure_twitter_api():
    API_KEY = get_config()['API_KEY']
    API_KEY_SECRET = get_config()['API_KEY_SECRET']

    ACCESS_TOKEN = get_config()['ACCESS_TOKEN']
    ACCESS_TOKEN_SECRET = get_config()['ACCESS_TOKEN_SECRET']

    auth = tweepy.OAuthHandler(API_KEY, API_KEY_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

    api = tweepy.API(auth, wait_on_rate_limit=True)
    return api


def get_twitter_api():
    global __API
    if not __API:
        __API = configure_twitter_api()
    return __API


if __name__ == '__main__':
    print(get_twitter_api())