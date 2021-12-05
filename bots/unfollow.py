import bots.utils as _utils
from dateutil.parser import parse
from bots.twitter_api import get_twitter_api
import random
import logging
import time
import datetime
from tweepy.errors import NotFound

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@_utils.random_execute(do_nothing_prob=.67, max_delay=120)
def unfollow(event=None, context=None):
    following_history = _utils.get_s3_data('following.json')

    sorted_by_following_date = sorted(
        [elem for elem in following_history.items() if 'unfollowed_at' not in elem[1]],
        key=lambda x: parse(x[1]['followed_at'])
    )

    number_to_unfollow = random.randint(1, 5)
    for currently_following in sorted_by_following_date[:number_to_unfollow]:
        _id = currently_following[0]

        try:
            api = get_twitter_api()
            api.destroy_friendship(user_id=_id)
            following_history[_id]['unfollowed_at'] = datetime.datetime.now().isoformat()
            logger.info(f'Unfollowing: {_id}')
        except NotFound as e:
            following_history[_id]['unfollowed_at'] = datetime.datetime.now().isoformat()
            logger.info(f'{_id} does not exist any longer, will mark as unfollowed')
        except Exception as e:
            logger.error(f'Unfollowing: {_id} did not work with error {e}')
        time.sleep(random.randint(2, 8))

    _utils.sync_s3_data(following_history)