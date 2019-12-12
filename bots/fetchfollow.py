import tweepy
from bots.twitter_api import get_twitter_api
import bots.utils as _utils
import datetime
import logging
import random
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COMMENTS = [
    'Nice piece!', 'Interesting', '👍', 'I am going to read up on this', 'Thanks for sharing!', 'This is helpful',
    'Insightful', 'thought-provoking', 'Will check this out'
]

HASHTAG_SETS = [
    {'Python', 'DataScience', 'Machinelearning'},
    {'Python', 'Keras'},
    {'Python', 'DataScience'},
    {'Python', 'Pandas'},
    {'Python', 'PyTorch', 'Machinelearning'},
    {'Python', 'Scikitlearn'},
    {'Python', 'Statisitcs'},
]


def fetch_most_original_tweets(user):
    results = []
    for tweet in get_twitter_api().user_timeline(user.id, count=20):
        if not (tweet.retweeted or tweet.in_reply_to_status_id):
            tweet.score = score_tweet(tweet)
            results.append(tweet)

    return results


def interact_with_user(user, following_history, hashtags):
    if not user.following:
        if random.random() > 0.4:
            logger.info(f"Following {user.name}")
            user.follow()
            following_history[user.id_str] = {'followed_at': datetime.datetime.now().isoformat()}

        user_tweets = sorted(fetch_most_original_tweets(user), key=lambda x: x.score, reverse=True)
        if len(user_tweets) > 0:
            interactions = 0
            for tweet in user_tweets:
                tags = {tag['text'].lower() for tag in tweet.entities.get('hashtags')}
                lower_given_tag = {tag.lower() for tag in hashtags}
                for given_tag in lower_given_tag:
                    if given_tag in tweet.text.lower():
                        found_tag_in_text = True
                        break
                else:
                    found_tag_in_text = False

                if (len(tags & lower_given_tag) > 0) or found_tag_in_text:
                    interaction = 0

                    if random.random() > 0.95:
                        comment = f'@{user.screen_name} {random.choice(COMMENTS)}'
                        logger.info(f"Commenting: {tweet.id} with: {comment}")
                        get_twitter_api().update_status(
                            comment,
                            in_reply_to_status_id=tweet.id_str,
                            auto_populate_reply_metadata=True
                        )
                        time.sleep(random.random()/2)
                        interaction |= 1

                    if not tweet.favorited and (random.random() > .5) and tweet.lang == 'en':
                        logger.info(f"Hearting: {tweet.id} with text: {tweet.text}")
                        get_twitter_api().create_favorite(tweet.id)
                        time.sleep(random.random() * 5)
                        interaction |= 1

                    if random.random() > 0.95:
                        logger.info(f"Retweeting: {tweet.id}")
                        logger.info(f"Text: {tweet.text}")
                        get_twitter_api().retweet(tweet.id)
                        time.sleep(random.random())
                        interaction |= 1

                    interactions += interaction

                if interactions == 2:
                    break


def score_tweet(tweet):
    favorites = _utils.scaled_sigmoid(x=-tweet.favorite_count, stretch=2, max_score=50, center=3)
    retweets = _utils.scaled_sigmoid(x=-tweet.retweet_count, stretch=1, max_score=50, center=2)
    age = _utils.created_at_score(tweet, stretch=2, max_score=30, center=3)
    score = favorites + retweets + age
    return score


def score_user(user):
    followed_to_following = _utils.followed_to_following_ratio(user)
    followers = _utils.scaled_sigmoid(x=-user.followers_count, stretch=200, max_score=100, center=300)
    age = _utils.created_at_score(user, stretch=50, max_score=30, center=60)
    score = followed_to_following + followers + age
    return score


def get_users_from_recent_tweets(cnt=10, hashtags=None):
    q = ' AND '.join([f'#{tag}' for tag in hashtags])

    users = []
    for tweet in tweepy.Cursor(get_twitter_api().search, q=q, lang="en", count=cnt, result_type='recent').items(cnt):
        users.append(tweet.user)

    return users


@_utils.random_execute(do_nothing_prob=.6, max_delay=120)
def fetchfollow(event=None, context=None):
    hashtags = random.choice(HASHTAG_SETS)

    # monkey-patch the tweepy User class by adding a hashfunction, which we will need to quickly get unique users
    tweepy.models.User.__hash__ = lambda self: hash(self.id_str)
    users = list(set(get_users_from_recent_tweets(cnt=250, hashtags=hashtags)))

    # score users
    for user in users:
        user.score = score_user(user)

    # sort users by score
    users = sorted(users, key=lambda x: x.score, reverse=True)
    logger.info(f"Found {len(users)}")

    following_history = _utils.get_s3_data('following.json')

    max_interactions = 10
    interactions = 0
    for user in users:
        time.sleep(random.random() * 10 + 2)
        if user.id_str not in following_history:
            try:
                logger.info(f"Interacting with {user.name}")
                interact_with_user(user, following_history, hashtags)
                interactions += 1
            except Exception as e:
                logger.error(f'Syncing followers history on error: {e}')
                _utils.sync_s3_data(following_history)
                raise

        if interactions >= max_interactions:
            break

    logger.info('Syncing followers history on ordinary termination')
    _utils.sync_s3_data(following_history)


def comment_tweet(user, tweet):
    comment = f'@{user.screen_name} {random.choice(COMMENTS)}'
    logger.info(f"Commenting: {tweet.id} with: {comment}")
    get_twitter_api().update_status(
        comment,
        in_reply_to_status_id=tweet.id_str,
        auto_populate_reply_metadata=True
    )

if __name__ == '__main__':
    fetchfollow()

